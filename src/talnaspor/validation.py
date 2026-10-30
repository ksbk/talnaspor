"""Validate statistical value codes against allowed PX-Web values."""


def validate_value(requested: str, allowed: list[str]) -> str:
    """Return the requested code if it is allowed."""
    if requested not in allowed:
        raise ValueError(f"Unsupported value: {requested}")

    return requested
