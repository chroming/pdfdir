"""Cooperative cancellation primitives for long-running PDF operations."""


class OperationCancelled(RuntimeError):
    """Raised when the user cancels a background operation."""


def raise_if_cancelled(cancel_check=None):
    """Raise ``OperationCancelled`` when ``cancel_check`` requests it."""
    if cancel_check and cancel_check():
        raise OperationCancelled("Operation cancelled")
