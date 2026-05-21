import io
import os
import shlex
import tarfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from tempfile import TemporaryFile
from typing import Literal, Optional

from kubernetes.client import ApiClient, CoreV1Api
from kubernetes.stream import stream


EndpointKind = Literal["local", "pod"]


@dataclass(frozen=True)
class TransferEndpoint:
    kind: EndpointKind
    path: Path | PurePosixPath
    is_dir: bool
    container: Optional[str] = None

    @property
    def display(self) -> str:
        return f"{self.kind}:{self.path}"

    @property
    def name(self) -> str:
        name = self.path.name
        return name or str(self.path)


@dataclass(frozen=True)
class PodFileEntry:
    path: PurePosixPath
    is_dir: bool

    @property
    def label(self) -> str:
        # self.path == self.path.parent is possible when path is root "/"
        suffix = "/" if self.is_dir and self.path != self.path.parent else ""
        return f"{self.path.name or '/'}{suffix}"


class PodFileSystem:
    def __init__(
        self,
        api_client: ApiClient,
        pod_name: str,
        namespace: str,
        container_name: Optional[str] = None,
    ) -> None:
        self.core_api = CoreV1Api(api_client=api_client)
        self.pod_name = pod_name
        self.namespace = namespace
        self.container_name = container_name

    def list_dir(self, path: PurePosixPath | str) -> list[PodFileEntry]:
        pod_path = PurePosixPath(str(path) or "/")
        quoted_path = shlex.quote(str(pod_path))
        script = (
            f"p={quoted_path}; "
            'if [ ! -d "$p" ]; then echo "not a directory: $p" >&2; exit 2; fi; '
            'for entry in "$p"/* "$p"/.[!.]* "$p"/..?*; do '
            '[ -e "$entry" ] || continue; '
            'name=${entry##*/}; '
            'if [ -d "$entry" ]; then printf "d\\t%s\\n" "$name"; '
            'else printf "f\\t%s\\n" "$name"; fi; '
            "done"
        )
        output = self._exec(["sh", "-c", script])
        entries: list[PodFileEntry] = []
        for line in output.splitlines():
            if "\t" not in line:
                continue
            kind, name = line.split("\t", 1)
            if not name or name in {".", ".."}:
                continue
            entries.append(PodFileEntry(path=pod_path / name, is_dir=kind == "d"))
        entries.sort(key=lambda item: (not item.is_dir, item.path.name.lower()))
        return entries

    def _exec(self, command: list[str]) -> str:
        return stream(
            self.core_api.connect_get_namespaced_pod_exec,
            self.pod_name,
            self.namespace,
            command=command,
            container=self.container_name,
            stderr=True,
            stdin=False,
            stdout=True,
            tty=False,
            _preload_content=True,
        )


class PodFileTransfer:
    def __init__(
        self,
        api_client: ApiClient,
        pod_name: str,
        namespace: str,
        container_name: Optional[str] = None,
    ) -> None:
        self.core_api = CoreV1Api(api_client=api_client)
        self.pod_name = pod_name
        self.namespace = namespace
        self.container_name = container_name
        self._command_cache: dict[str, bool] = {}

    def upload(self, source: Path, dest_dir: PurePosixPath, dest_name: str) -> None:
        if not source.exists():
            raise FileNotFoundError(str(source))
        if not dest_name:
            raise ValueError("Destination name is required")

        if not self.has_command("tar"):
            self._upload_file_with_cat(source, dest_dir, dest_name)
            return
        self._upload_with_tar(source, dest_dir, dest_name)

    def download(
        self,
        source: PurePosixPath,
        dest_dir: Path,
        dest_name: str,
        source_is_dir: bool = False,
    ) -> None:
        if not dest_name:
            raise ValueError("Destination name is required")
        if not self.has_command("tar"):
            if source_is_dir:
                raise RuntimeError("Directory download requires tar in the container")
            self._download_file_with_cat(source, dest_dir, dest_name)
            return
        self._download_with_tar(source, dest_dir, dest_name)

    def has_command(self, command: str) -> bool:
        if command in self._command_cache:
            return self._command_cache[command]
        quoted = shlex.quote(command)
        output = stream(
            self.core_api.connect_get_namespaced_pod_exec,
            self.pod_name,
            self.namespace,
            command=["sh", "-c", f"command -v {quoted} >/dev/null 2>&1 && echo yes || echo no"],
            container=self.container_name,
            stderr=False,
            stdin=False,
            stdout=True,
            tty=False,
            _preload_content=True,
        )
        available = str(output).strip() == "yes"
        self._command_cache[command] = available
        return available

    def _upload_with_tar(self, source: Path, dest_dir: PurePosixPath, dest_name: str) -> None:
        quoted_dir = shlex.quote(str(dest_dir))
        command = ["sh", "-c", f"mkdir -p {quoted_dir} && tar xf - -C {quoted_dir}"]
        resp = self._open_exec(command, stdin=True)
        try:
            with TemporaryFile() as archive:
                with tarfile.open(fileobj=archive, mode="w") as tar:
                    tar.add(source, arcname=dest_name, recursive=True)
                archive.seek(0)
                while True:
                    chunk = archive.read(1024 * 256)
                    if not chunk:
                        break
                    resp.write_stdin(chunk)
            resp.write_stdin(b"")
            self._drain_response(resp)
        finally:
            resp.close()

    def _upload_file_with_cat(self, source: Path, dest_dir: PurePosixPath, dest_name: str) -> None:
        if source.is_dir():
            raise RuntimeError("Directory upload requires tar in the container")

        dest_path = dest_dir / dest_name
        quoted_dir = shlex.quote(str(dest_dir))
        quoted_dest = shlex.quote(str(dest_path))
        command = ["sh", "-c", f"mkdir -p {quoted_dir} && cat > {quoted_dest}"]
        resp = self._open_exec(command, stdin=True)
        try:
            with source.open("rb") as source_file:
                while True:
                    chunk = source_file.read(1024 * 256)
                    if not chunk:
                        break
                    resp.write_stdin(chunk)
            self._drain_response(resp)
        finally:
            resp.close()

    def _download_with_tar(self, source: PurePosixPath, dest_dir: Path, dest_name: str) -> None:
        dest_dir.mkdir(parents=True, exist_ok=True)
        parent = str(source.parent) if str(source.parent) else "/"
        source_name = source.name or "."
        command = [
            "sh",
            "-c",
            f"tar cf - -C {shlex.quote(parent)} {shlex.quote(source_name)}",
        ]
        resp = self._open_exec(command, stdin=False)
        try:
            archive_data = io.BytesIO()
            empty_reads = 0
            while resp.is_open():
                resp.update(timeout=1)
                stdout = resp.read_channel(1, timeout=0)
                if stdout:
                    if isinstance(stdout, str):
                        stdout = stdout.encode()
                    archive_data.write(stdout)
                    empty_reads = 0
                stderr = resp.read_channel(2, timeout=0)
                if stderr:
                    raise RuntimeError(self._channel_text(stderr).strip())
                if not stdout:
                    empty_reads += 1
                if empty_reads >= 3:
                    break
            archive_data.seek(0)
            with tarfile.open(fileobj=archive_data, mode="r:*") as tar:
                self._safe_extract(tar, dest_dir)
            extracted = dest_dir / source_name
            target = dest_dir / dest_name
            if extracted != target and extracted.exists():
                if target.exists():
                    raise FileExistsError(str(target))
                os.replace(extracted, target)
        finally:
            resp.close()

    def _download_file_with_cat(self, source: PurePosixPath, dest_dir: Path, dest_name: str) -> None:
        dest_dir.mkdir(parents=True, exist_ok=True)
        target = dest_dir / dest_name
        command = ["sh", "-c", f"cat {shlex.quote(str(source))}"]
        resp = self._open_exec(command, stdin=False)
        try:
            data = self._read_stdout_response(resp)
            target.write_bytes(data)
        finally:
            resp.close()

    def _open_exec(self, command: list[str], stdin: bool):
        return stream(
            self.core_api.connect_get_namespaced_pod_exec,
            self.pod_name,
            self.namespace,
            command=command,
            container=self.container_name,
            stderr=True,
            stdin=stdin,
            stdout=True,
            tty=False,
            binary=True,
            _preload_content=False,
        )

    def _drain_response(self, resp) -> None:
        errors: list[str] = []
        empty_reads = 0
        while resp.is_open():
            resp.update(timeout=1)
            stderr = resp.read_channel(2, timeout=0)
            if stderr:
                errors.append(self._channel_text(stderr))
            stdout = resp.read_channel(1, timeout=0)
            if stderr or stdout:
                empty_reads = 0
            else:
                empty_reads += 1
            if empty_reads >= 3:
                break
        if errors:
            raise RuntimeError("".join(errors).strip())

    def _read_stdout_response(self, resp) -> bytes:
        output = io.BytesIO()
        errors: list[str] = []
        empty_reads = 0
        while resp.is_open():
            resp.update(timeout=1)
            stdout = resp.read_channel(1, timeout=0)
            if stdout:
                if isinstance(stdout, str):
                    stdout = stdout.encode()
                output.write(stdout)
                empty_reads = 0
            stderr = resp.read_channel(2, timeout=0)
            if stderr:
                errors.append(self._channel_text(stderr))
                empty_reads = 0
            if not stdout and not stderr:
                empty_reads += 1
            if empty_reads >= 3:
                break
        if errors:
            raise RuntimeError("".join(errors).strip())
        return output.getvalue()

    def _channel_text(self, value: bytes | str) -> str:
        if isinstance(value, bytes):
            return value.decode("utf-8", "replace")
        return value

    def _safe_extract(self, tar: tarfile.TarFile, dest_dir: Path) -> None:
        """
        Extracts a tar file to the specified destination directory while 
          preventing path traversal attacks and local file or directory were
          overwritten by downloaded files
        """
        base = dest_dir.resolve()
        for member in tar.getmembers():
            target = (dest_dir / member.name).resolve()
            if base not in target.parents and target != base:
                raise RuntimeError(f"Unsafe tar path: {member.name}")
        tar.extractall(dest_dir)
