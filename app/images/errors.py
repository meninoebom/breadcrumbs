"""Errors raised by the image pipeline. Callers map these to HTTP status codes."""


class ImageGenerationError(RuntimeError):
    """Upstream failure while generating candidate images (missing token, provider error, empty output)."""


class ImageCommitError(RuntimeError):
    """Failure while validating or persisting a chosen candidate (bad host, bad payload, upload error)."""
