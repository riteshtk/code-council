"""CodeCouncil API server entry point."""
from codecouncil.api.app import create_app

app = create_app()
