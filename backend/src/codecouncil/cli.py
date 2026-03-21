"""CodeCouncil CLI."""

import typer

app = typer.Typer(name="codecouncil", help="AI agent council for codebase intelligence")


@app.command()
def analyse(repo: str):
    """Analyse a repository with the council."""
    typer.echo(f"Analysing {repo}...")


if __name__ == "__main__":
    app()
