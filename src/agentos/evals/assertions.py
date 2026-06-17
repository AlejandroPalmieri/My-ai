from __future__ import annotations

from typing import Any


def assert_true(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def assert_equal(actual: Any, expected: Any, message: str) -> None:
    if actual != expected:
        raise AssertionError(f"{message} Expected {expected!r}, got {actual!r}.")


def assert_in(member: object, container: object, message: str) -> None:
    if member not in container:  # type: ignore[operator]
        raise AssertionError(message)


def assert_not_in(member: object, container: object, message: str) -> None:
    if member in container:  # type: ignore[operator]
        raise AssertionError(message)
