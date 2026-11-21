"""Vercel's recognized WSGI entrypoint."""
from deployment.vercel import configured_app

app = configured_app()
