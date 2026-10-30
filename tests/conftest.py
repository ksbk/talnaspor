from collections.abc import Iterator

import pytest

from talnaspor import pxweb


@pytest.fixture(autouse=True)
def empty_pxweb_cache() -> Iterator[None]:
    """Keep cached PX-Web responses from leaking between tests."""
    pxweb.clear_cache()
    yield
    pxweb.clear_cache()
