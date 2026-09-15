from collections.abc import Generator
from contextlib import contextmanager

from unihttp.exceptions import UniHTTPError

ErrorMap = dict[type[UniHTTPError], type[BaseException] | tuple[type[BaseException], ...]]


@contextmanager
def translate_errors(mapping: ErrorMap) -> Generator[None, None, None]:
    """Re-raise backend exceptions as unihttp ones; the first matching entry wins."""
    try:
        yield
    except Exception as e:
        for target, types in mapping.items():
            if isinstance(e, types):
                raise target(str(e)) from e
        raise
