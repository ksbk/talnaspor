"""Validate statistical value codes against allowed PX-Web values."""


class UnavailableValue(ValueError):
    """A requested value that the table does not contain, such as a year it does not cover.

    first and last are the labels of the table's first and last values for that dimension,
    so the reply can say what is available.
    """

    def __init__(self, requested: str, dimension: str, first: str, last: str) -> None:
        super().__init__(f"Unsupported value: {requested}")
        self.requested = requested
        self.dimension = dimension
        self.first = first
        self.last = last


def validate_value(
    requested: str, allowed: list[str], dimension: str = "", labels: list[str] | None = None
) -> str:
    """Return the requested code if it is allowed."""
    if requested not in allowed:
        shown = labels or allowed
        raise UnavailableValue(requested, dimension, shown[0], shown[-1])

    return requested
