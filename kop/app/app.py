import os
import argparse
import difflib
from textual.app import App, ComposeResult
from kop.views.ResourceView import ResourceView
from kop.views.StartupView import ConfigView
from kop.provider.config import ConfigModel, Config
from kop.provider.client import KbsEndpoint




class Kop(App):
    TITLE = "Kop"

    def __init__(self, config_file: str | None = None, **kwargs):
        """
        `config_file` is the path to the local kubuconfig file 
        specified by the user when starting Kop using the 
        `--kubeconfig` parameter.
        """

        super().__init__(**kwargs)
        self.endpoint: KbsEndpoint | None = None
        self.config_file = config_file

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
        
    
    def _get_configs(self) -> list[ConfigModel]:
        """
        retrieve all synchronized kubuconfig files in the kop working directory
        """
        return Config().get_configs()
    

def get_args() -> str | None:
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
    kop = Kop(config_file=get_args())
    kop.run()


if __name__ == "__main__":
    run()