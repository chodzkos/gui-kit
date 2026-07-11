"""Strażnik wersji: ``__version__`` pochodzi z metadanych pakietu (jedno źródło prawdy).

Łapie regresję, w której ktoś ponownie wpisałby literał wersji do ``__init__.py``
zamiast czytać ją z metadanych (pole ``version`` w ``pyproject.toml``). Czysty
Python — bez PySide6.
"""

from __future__ import annotations

from importlib.metadata import version

import chodzkos_gui_kit


def test_version_matches_package_metadata() -> None:
    """__version__ == metadane zainstalowanego pakietu (a nie fallback)."""
    assert chodzkos_gui_kit.__version__ == version("chodzkos-gui-kit")
    assert chodzkos_gui_kit.__version__ != "0.0.0+unknown"
