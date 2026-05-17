import webbrowser


def maybe_open_forward_in_browser(open_in_browser: bool, local_port: int) -> None:
    """Open forwarded local endpoint in browser when enabled."""
    if open_in_browser:
        webbrowser.open(f"http://127.0.0.1:{local_port}", new=2)
