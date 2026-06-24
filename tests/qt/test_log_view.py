"""Testy widgetu :class:`LogView` (warstwa qt/widgets) — offscreen, marker qt."""

from __future__ import annotations

import re

import pytest
from PySide6.QtGui import QColor
from pytestqt.qtbot import QtBot

from chodzkos_gui_kit import palette as pal
from chodzkos_gui_kit.qt.widgets.log_view import _MAX_BLOCKS, LogView

pytestmark = pytest.mark.qt


def _block_color(log: LogView, index: int) -> str:
    """Kolor (hex) tekstu w bloku ``index`` — z formatu fragmentu dokumentu."""
    block = log.document().findBlockByNumber(index)
    fragment = block.begin().fragment()
    return fragment.charFormat().foreground().color().name()


def test_levels_map_to_palette_roles(qtbot: QtBot) -> None:
    """5 poziomów + fallback mapuje się na właściwe role palety."""
    log = LogView()
    qtbot.addWidget(log)
    log.set_theme(pal.DARK)
    assert log._color_for("ok") == pal.DARK.accent
    assert log._color_for("warn") == pal.DARK.amber
    assert log._color_for("err") == pal.DARK.red
    assert log._color_for("cmd") == pal.DARK.fg3
    assert log._color_for("info") == pal.DARK.fg2
    assert log._color_for("nieznany") == pal.DARK.fg


def test_log_info_maps_to_ok_not_muted_info(qtbot: QtBot) -> None:
    """Pułapka semantyczna: log_info → poziom 'ok' (akcent), NIE wyszarzony 'info'."""
    log = LogView()
    qtbot.addWidget(log)
    log.set_theme(pal.DARK)
    log.log_info("hej")
    level = log._buffer[-1][0]
    assert level == "ok"
    assert log._color_for(level) == pal.DARK.accent
    assert pal.DARK.accent != pal.DARK.fg2  # sanity: to naprawdę różne kolory


def test_wrappers_map_warn_and_err(qtbot: QtBot) -> None:
    log = LogView()
    qtbot.addWidget(log)
    log.log_warning("w")
    log.log_error("e")
    assert log._buffer[-2][0] == "warn"
    assert log._buffer[-1][0] == "err"


def test_set_theme_rerenders_existing_history(qtbot: QtBot) -> None:
    """Zmiana motywu przemalowuje ISTNIEJĄCE wpisy, nie tylko nowe."""
    log = LogView()
    qtbot.addWidget(log)
    log.set_theme(pal.DARK)
    log.append_line("hello", "ok")
    assert _block_color(log, 0) == QColor(pal.DARK.accent).name()

    log.set_theme(pal.LIGHT)
    assert _block_color(log, 0) == QColor(pal.LIGHT.accent).name()


def test_max_blocks_limit_holds(qtbot: QtBot) -> None:
    """Po przekroczeniu limitu i bufor, i widok trzymają się _MAX_BLOCKS."""
    log = LogView()
    qtbot.addWidget(log)
    for i in range(_MAX_BLOCKS + 50):
        log.append_line(f"line {i}", "info")
    assert len(log._buffer) == _MAX_BLOCKS
    assert log.blockCount() <= _MAX_BLOCKS


def test_timestamps_optional(qtbot: QtBot) -> None:
    """timestamps=True prependuje [HH:MM:SS]; domyślnie brak."""
    with_ts = LogView(timestamps=True)
    qtbot.addWidget(with_ts)
    with_ts.append_line("hej", "info")
    first = with_ts.toPlainText().splitlines()[0]
    assert re.match(r"^\[\d\d:\d\d:\d\d\] hej$", first)
    assert with_ts._buffer[-1][2] != ""

    plain = LogView()
    qtbot.addWidget(plain)
    plain.append_line("hej", "info")
    assert plain.toPlainText().splitlines()[0] == "hej"


def test_level_colors_extensible_and_theme_aware(qtbot: QtBot) -> None:
    """Dodatkowy poziom przez level_colors (rola palety przeżywa zmianę motywu)."""
    log = LogView(level_colors={"transcribing": "accent2"})
    qtbot.addWidget(log)
    log.set_theme(pal.DARK)
    assert log._color_for("transcribing") == pal.DARK.accent2
    log.set_theme(pal.LIGHT)
    assert log._color_for("transcribing") == pal.LIGHT.accent2


def test_level_colors_accepts_direct_color(qtbot: QtBot) -> None:
    """level_colors może podać gotowy kolor (gdy nie jest nazwą roli palety)."""
    log = LogView(level_colors={"x": "#abcdef"})
    qtbot.addWidget(log)
    assert log._color_for("x") == "#abcdef"


def test_clear_resets_view_and_buffer(qtbot: QtBot) -> None:
    log = LogView()
    qtbot.addWidget(log)
    log.append_line("a", "ok")
    log.clear()
    assert log._buffer == []
    assert log.toPlainText() == ""
