class WorkerRuntimeError(Exception):
    """Base error for a worker job that can be safely recorded in job events."""


class ProviderConfigurationError(WorkerRuntimeError):
    """Raised when provider credentials or settings are unavailable."""


class ProviderRequestError(WorkerRuntimeError):
    """Raised when a provider request cannot produce a usable response."""


class ProviderResponseFormatError(ProviderRequestError):
    """Provider returned content that cannot be decoded as the requested JSON."""

    def __init__(self, message: str, *, provider_name: str, content: str, finish_reason: str | None) -> None:
        super().__init__(message)
        self.provider_name = provider_name
        self.content = content
        self.finish_reason = finish_reason


class OutputValidationError(WorkerRuntimeError):
    """Raised when model output does not satisfy the worker JSON schema."""
