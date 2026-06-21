"""Testy IconProvider — przebarwialne SVG wg palety (offscreen)."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from chodzkos_gui_kit.palette import DARK, LIGHT
from chodzkos_gui_kit.qt import icons

pytestmark = pytest.mark.qt


@pytest.fixture(autouse=True)
def _clear_icon_cache() -> None:
    """Każdy test startuje z czystym cache ikon."""
    icons.clear_cache()


def test_icon_map_files_exist_in_package() -> None:
    """Każdy plik z ICON_MAP da się wczytać z assetów pakietu (bez Qt)."""
    for name in icons.ICON_MAP:
        svg = icons._load_recolored_svg(name, "#123456")
        assert svg is not None, name
        assert "currentColor" not in svg  # podmienione na kolor
        assert "#123456" in svg


def test_get_icon_returns_non_null(qapp: QApplication) -> None:
    """Znana akcja → niepusta QIcon, zapisana w cache."""
    icon = icons.get_icon("save")
    assert not icon.isNull()
    assert len(icons._cache) == 1


def test_same_name_two_colors_two_cache_entries(qapp: QApplication) -> None:
    """Ta sama nazwa w dwóch kolorach → dwa różne wpisy cache."""
    icons.get_icon("save", "fg")
    icons.get_icon("save", "red")
    assert len(icons._cache) == 2
    # ponowne wywołanie tego samego klucza nie dokłada wpisu
    icons.get_icon("save", "fg")
    assert len(icons._cache) == 2


def test_clear_cache_empties(qapp: QApplication) -> None:
    """clear_cache czyści zapamiętane ikony (do wołania na theme_changed)."""
    icons.get_icon("save")
    assert icons._cache
    icons.clear_cache()
    assert icons._cache == {}


def test_unknown_name_returns_empty_icon_uncached(qapp: QApplication) -> None:
    """Nieznana akcja → pusta QIcon i brak wpisu w cache (bez wyjątku)."""
    icon = icons.get_icon("does-not-exist")
    assert icon.isNull()
    assert icons._cache == {}


def test_color_none_defaults_to_fg() -> None:
    """color=None rozwiązuje się do roli fg bieżącej palety (domyślny token)."""
    assert icons._DEFAULT_TOKEN == "fg"
    assert icons._resolve_color(icons._DEFAULT_TOKEN, DARK) == DARK.fg


def test_resolve_color_tokens_from_palette() -> None:
    """Tokeny semantyczne mapują na pola palety; nieznany → fg."""
    assert icons._resolve_color("red", DARK) == DARK.red
    assert icons._resolve_color("amber", DARK) == DARK.amber
    assert icons._resolve_color("accent", DARK) == DARK.accent
    assert icons._resolve_color("bez-takiego-tokena", DARK) == DARK.fg


def test_accent_text_token_honours_light_contrast_rule() -> None:
    """Token accent_text: dark→accent, light→accent2 (reguła kontrastu §5)."""
    assert icons._resolve_color("accent_text", DARK) == DARK.accent
    assert icons._resolve_color("accent_text", LIGHT) == LIGHT.accent2
    # surowy accent w jasnym motywie to wciąż jasny accent (świadomy wybór konsumenta)
    assert icons._resolve_color("accent", LIGHT) == LIGHT.accent


def test_resolve_color_uses_current_palette(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bez jawnej palety token bierze kolor z current_palette()."""
    monkeypatch.setattr(icons, "current_palette", lambda: LIGHT)
    assert icons._resolve_color("fg") == LIGHT.fg
