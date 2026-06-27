"""Testy widgetu :class:`HelpWindow` i helperów HTML — offscreen, marker qt."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QTabWidget
from pytestqt.qtbot import QtBot

from chodzkos_gui_kit.qt.widgets import help_html
from chodzkos_gui_kit.qt.widgets.help_window import HelpWindow

pytestmark = pytest.mark.qt


def _tab_widget(window: HelpWindow) -> QTabWidget:
    """Jedyny QTabWidget okna (zakładki)."""
    return window.findChild(QTabWidget)


def test_tabs_injected_one_per_entry(qtbot: QtBot) -> None:
    """Każdy wpis (tytuł, html) daje jedną zakładkę o właściwym tytule."""
    window = HelpWindow(tabs=[("A", "<p>x</p>"), ("B", "<p>y</p>")])
    qtbot.addWidget(window)
    tabs = _tab_widget(window)
    assert tabs.count() == 2
    assert tabs.tabText(0) == "A"
    assert tabs.tabText(1) == "B"
    assert len(window._browsers) == 2


def test_title_defaults_to_help_and_is_overridable(qtbot: QtBot) -> None:
    default = HelpWindow()
    qtbot.addWidget(default)
    assert default.windowTitle() == "Help"

    custom = HelpWindow(title="Pomoc — pdf2md", tabs=[("A", "<p>x</p>")])
    qtbot.addWidget(custom)
    assert custom.windowTitle() == "Pomoc — pdf2md"


def test_no_tabs_constructs_empty(qtbot: QtBot) -> None:
    """tabs=None → okno bez zakładek, bez wyjątku."""
    window = HelpWindow()
    qtbot.addWidget(window)
    assert _tab_widget(window).count() == 0
    assert window._browsers == []


def test_palette_change_re_sets_same_html_on_every_browser(qtbot: QtBot) -> None:
    """changeEvent(PaletteChange) woła setHtml PONOWNIE — tym samym html — na każdym browserze."""
    window = HelpWindow(tabs=[("A", "<p>x</p>"), ("B", "<p>y</p>")])
    qtbot.addWidget(window)

    calls: list[tuple[int, str]] = []
    for idx, (browser, _html) in enumerate(window._browsers):

        def _spy(html: str, _idx: int = idx) -> None:
            calls.append((_idx, html))

        browser.setHtml = _spy  # type: ignore[method-assign]

    window.changeEvent(QEvent(QEvent.Type.PaletteChange))

    # Po jednym re-secie na browser, każdy z ORYGINALNYM html z tabs.
    assert calls == [(0, "<p>x</p>"), (1, "<p>y</p>")]


def test_non_palette_change_event_does_not_re_render(qtbot: QtBot) -> None:
    """Inne changeEvent (np. zmiana aktywacji) nie przemalowują zakładek."""
    window = HelpWindow(tabs=[("A", "<p>x</p>")])
    qtbot.addWidget(window)

    called = False
    browser, _html = window._browsers[0]

    def _spy(_html: str) -> None:
        nonlocal called
        called = True

    browser.setHtml = _spy  # type: ignore[method-assign]
    window.changeEvent(QEvent(QEvent.Type.ActivationChange))
    assert called is False


def test_helpers_produce_expected_html() -> None:
    assert help_html.section("Tytuł", "<p>x</p>") == "<h3>Tytuł</h3><p>x</p>"
    assert help_html.paragraph("hej") == "<p>hej</p>"
    assert help_html.unordered_list("a", "b") == "<ul><li>a</li><li>b</li></ul>"


def test_table_renders_headers_and_rows() -> None:
    html = help_html.table(["H1", "H2"], [["a", "b"], ["c", "d"]])
    assert "<th style='padding:4px 8px;text-align:left'>H1</th>" in html
    assert "<td style='padding:4px 8px'>a</td>" in html
    assert "<td style='padding:4px 8px'>d</td>" in html
    # Nagłówek na powierzchni motywu (palette), nie hex.
    assert "palette(alternate-base)" in html
    assert "#" not in html


def test_code_and_pre_use_palette_surface_not_hex() -> None:
    for html in (help_html.code("x"), help_html.preformatted("y")):
        assert "palette(alternate-base)" in html
        assert "palette(text)" in html
        assert "#" not in html
