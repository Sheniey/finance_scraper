"""HTTP API for the finance scraper."""


# ================================================== #
# MODULE: __init__
# ================================================== #

__all__: list[str] = ['app']


def __getattr__(name: str) -> object:
    if name != 'app':
        raise AttributeError(name)
    from api.core.main import app

    return app