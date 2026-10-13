
import tomllib, subprocess
from rich.console import Console
from typing import Final as Const, Annotated
from typer import Typer, Argument, Option


# ================================================== #
# DEVELOPMENT CLI                                    #
# ================================================== #

app: Typer = Typer()
console: Console = Console()
PYPROJECT_FILE: Const[str] = 'pyproject.toml'


@app.command(
    name='run',
    help='Run the development command'
)
def run(
    script: Annotated[str, Argument(..., help='The script to run')] = None,
    listing: Annotated[bool, Option(..., '--list', '-l', help='Whether to list all available scripts')] = False,
    options: Annotated[list[str], Argument(..., help='Additional options for the script')] = [],
):
    with open(PYPROJECT_FILE, 'rb') as f:
        config = tomllib.load(f)
    scripts: dict[str, list[str]] = config.get('tool', {}).get('scripts', {})

    if listing:
        console.print('[i] Available scripts:', style='bold green')
        for name in sorted(scripts.keys()):
            console.print(f' - {name}')
        return

    command: list[str] = scripts.get(script)
    if command:
        for subcmd in command:
            console.print(f'> {subcmd}', style='cyan')
            subprocess.run(subcmd + ' ' + ' '.join(options), check=True, shell=True)
    else:
        console.print(f"\\[!] Script '{script}' not found.", style='bold red')


if __name__ == '__main__':
    app()
