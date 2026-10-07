from contextlib import ExitStack

import pytest

from src.pdf.pdf import Pdf


@pytest.fixture
def managed_pdf():
    """Tests using the low-level API own the same explicit lifetime as callers."""
    with ExitStack() as stack:
        yield lambda *args, **kwargs: stack.enter_context(Pdf(*args, **kwargs))
