"""Compatibility entrypoint for the FastAPI application."""

from api.core.main import app


# ================================================== #
# PUBLIC ENTRYPOINT                                  #
# ================================================== #

__all__: list[str] = ['app']
