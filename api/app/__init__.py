from __future__ import annotations

"""Tactyo API package."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("tactyo-api")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"
