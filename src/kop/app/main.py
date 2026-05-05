import os
import argparse
import difflib
from pathlib import Path
from importlib.metadata import PackageNotFoundError, version
from textual.app import App
from kop.views.ResourceView import ResourceView
from kop.views.StartupView import ConfigView
from kop.provider.config import ConfigModel, Config
from kop.provider.client import KbsEndpoint
from typing import Optional




class Kop(App):
    TITLE = "Kop"

    def __init__(self, config_file: Optional[str] = None, **kwargs):
        """
        `config_file` is the path to the local kubuconfig file 
        specified by the user when starting Kop using the 
        `--kubeconfig` parameter.
        """

        super().__init__(**kwargs)
        self.endpoint: Optional[KbsEndpoint] = None
        self.config_file = config_file

    def _close_endpoint(self) -> None:
        endpoint = self.endpoint
        if not endpoint:
            return
        close = getattr(endpoint, "close", None)
        if callable(close):
            close()
        self.endpoint = None

    def on_mount(self) -> None:
        if self.config_file:
            self.endpoint = KbsEndpoint(config_file=self.config_file)
            self.view = view = ResourceView()
            self.view.sub_title = self.config_file
            self.push_screen(view)
            return
        start_view = ConfigView(kubeconfigs=self._get_configs())
        self.push_screen(
            start_view
            )
        self.home = start_view

    def on_unmount(self) -> None:
        self._close_endpoint()

    # def action_quit(self) -> None:
    #     self._close_endpoint()
    #     super().action_quit()
        
    
    def _get_configs(self) -> list[ConfigModel]:
        """
        retrieve all synchronized kubuconfig files in the kop working directory
        """
        return Config().get_configs()
    

def get_app_version() -> str:
    """Resolve Kop version from installed metadata, with a source fallback."""
    try:
        return version("kop-cli")
    except PackageNotFoundError:
        init_file = Path(__file__).resolve().parents[1] / "__init__.py"
        if init_file.is_file():
            with init_file.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("__version__"):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
    return "unknown"


def get_args() -> Optional[str]:
    """
    retrieves the value of the `--kubeconfig` parameter specified on the command line when starting Kop.
    includes typo suggestion and validation.
    """

    parser = argparse.ArgumentParser(description="Kop CLI")

    parser.add_argument(
        "--kubeconfig",
        type=valid_file,
        help="Path to kubeconfig file"
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {get_app_version()}"
    )

    valid_args = ["--kubeconfig"]
    for action in parser._actions:
        valid_args.extend(action.option_strings)

    args, unknown = parser.parse_known_args()

    if unknown:
        for arg in unknown:
            if arg.startswith("--"):
                suggestion = difflib.get_close_matches(arg, valid_args, n=1)
                if suggestion:
                    parser.error(
                        f"unknown argument: {arg}\nDid you mean {suggestion[0]}?"
                    )
                else:
                    parser.error(f"unknown argument: {arg}")
        return
            
    return args.kubeconfig


def valid_file(path: str) -> str:
    if not os.path.exists(path):
        raise argparse.ArgumentTypeError(f"Path does not exist: {path}")
    if not os.path.isfile(path):
        raise argparse.ArgumentTypeError(f"Not a file: {path}")
    valid, _ = Config().validate_config(path)
    if not valid:
        raise argparse.ArgumentTypeError(f"Invalid kubeconfig file: {path}")
    return path


def run() -> None:
    print(f"\033]0;kop\007", end="", flush=True)
    kop = Kop(config_file=get_args())
    kop.run()


if __name__ == "__main__":
    run()
