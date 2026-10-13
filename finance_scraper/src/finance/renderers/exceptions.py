# ================================================== #
# MODULE: exceptions
# ================================================== #


class RenderError(Exception):
    """Base class for rendering errors."""
    pass

class RendererNotFoundError(RenderError):
    """Raised when a renderer is not found."""
    def __init__(self, renderer_name: str):
        self.renderer_name = renderer_name
        super().__init__(f"Unknown renderer: '{renderer_name}'. It was not found in the available renderers.")
