from __future__ import annotations

from dataclasses import dataclass

from src.modal_app import MODAL_APP


class AttioError(Exception):
    pass


class ConfigurationError(AttioError):
    pass


class ConnectivityError(AttioError):
    pass


class SchemaMismatchError(AttioError):
    def __init__(self, message: str, *, field: str | None = None) -> None:
        super().__init__(message)
        self.field = field


class ValidationError(AttioError):
    pass


class ConflictError(AttioError):
    def __init__(self, message: str, *, existing_record_id: str | None = None) -> None:
        super().__init__(message)
        self.existing_record_id = existing_record_id


class AttioAuthError(AttioError):
    pass


class AttioNotFoundError(AttioError):
    pass


class DeploymentMismatchError(AttioError):
    pass


class AttioConflictError(ConflictError):
    pass


class AttioValidationError(ValidationError):
    pass


@dataclass
class ClassifiedError:
    code: str
    message: str
    error_type: str
    fatal: bool
    field: str | None = None


def translate_modal_signature_error(error: Exception) -> Exception:
    if isinstance(error, TypeError) and "unexpected keyword argument" in str(error):
        return DeploymentMismatchError(
            "Modal function signature mismatch. Deployed function is stale for current CLI payload. "
            f"Redeploy with: modal app stop {MODAL_APP} && modal deploy deploy.py --name {MODAL_APP}",
        )
    return error


def classify_error(error: Exception, *, strict: bool = False) -> ClassifiedError:
    if isinstance(error, DeploymentMismatchError):
        return ClassifiedError(
            code="modal_signature_mismatch",
            message=str(error),
            error_type=type(error).__name__,
            fatal=True,
        )
    if isinstance(error, ConfigurationError):
        return ClassifiedError(
            code="configuration_error",
            message=str(error),
            error_type=type(error).__name__,
            fatal=True,
        )
    if isinstance(error, ConnectivityError):
        return ClassifiedError(
            code="connectivity_error",
            message=str(error),
            error_type=type(error).__name__,
            fatal=True,
        )
    if isinstance(error, SchemaMismatchError):
        return ClassifiedError(
            code="schema_mismatch",
            message=str(error),
            error_type=type(error).__name__,
            fatal=strict,
            field=error.field,
        )
    if isinstance(error, ConflictError):
        return ClassifiedError(
            code="conflict",
            message=str(error),
            error_type=type(error).__name__,
            fatal=True,
        )
    if isinstance(error, (ValidationError, AttioValidationError)):
        return ClassifiedError(
            code="validation_error",
            message=str(error),
            error_type=type(error).__name__,
            fatal=True,
        )

    return ClassifiedError(
        code="unknown_error",
        message=str(error),
        error_type=type(error).__name__,
        fatal=True,
    )
