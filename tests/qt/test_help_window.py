"""Testy widgetu :class:`HelpWindow` i helperów HTML — offscreen, marker qt."""

from __future__ import annotations

from pathlib import Path

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
    for idx, (browser, _content, _md) in enumerate(window._browsers):

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
    browser, _content, _md = window._browsers[0]

    def _spy(_html: str) -> None:
        nonlocal called
        called = True

    browser.setHtml = _spy  # type: ignore[method-assign]
    window.changeEvent(QEvent(QEvent.Type.ActivationChange))
    assert called is False


def test_add_markdown_section_renders_headings_and_code(qtbot: QtBot) -> None:
    """Zakładka Markdown renderuje nagłówki i bloki kodu (setMarkdown), bez surowych znaczników."""
    window = HelpWindow()
    qtbot.addWidget(window)
    window.add_markdown_section("Doc", "# Nagłówek\n\nAkapit.\n\n```\nkod tutaj\n```\n")

    tabs = _tab_widget(window)
    assert tabs.count() == 1 and tabs.tabText(0) == "Doc"
    browser, _content, markdown = window._browsers[0]
    assert markdown is True
    text = browser.toPlainText()
    assert "Nagłówek" in text and "kod tutaj" in text
    assert "#" not in text  # markdown zrenderowany, nie dosłowny (znacznik nagłówka zniknął)
    assert "<h1" in browser.toHtml().lower()  # nagłówek jako element, nie tekst


def test_add_markdown_section_from_file(qtbot: QtBot, tmp_path: Path) -> None:
    """``source: Path`` czyta plik przy dołożeniu (jeden plik prawdy — treść z docs/*.md)."""
    md = tmp_path / "doc.md"
    md.write_text("# Tytuł pliku\n\ntreść z pliku\n", encoding="utf-8")
    window = HelpWindow()
    qtbot.addWidget(window)
    window.add_markdown_section("Plik", md)

    browser, content, markdown = window._browsers[0]
    assert markdown is True
    assert "Tytuł pliku" in browser.toPlainText()
    # Surowy markdown zachowany do re-renderu na zmianę motywu.
    assert content == "# Tytuł pliku\n\ntreść z pliku\n"


def test_markdown_palette_change_re_renders_via_set_markdown(qtbot: QtBot) -> None:
    """PaletteChange re-renderuje zakładkę Markdown przez setMarkdown (NIE setHtml)."""
    window = HelpWindow()
    qtbot.addWidget(window)
    window.add_markdown_section("Doc", "# H\n")
    browser, _content, _md = window._browsers[0]

    calls: list[str] = []
    browser.setMarkdown = lambda md: calls.append(md)  # type: ignore[method-assign]
    browser.setHtml = lambda html: calls.append(f"HTML:{html}")  # type: ignore[method-assign]

    window.changeEvent(QEvent(QEvent.Type.PaletteChange))
    assert calls == ["# H\n"]  # tą samą metodą (setMarkdown), tą samą treścią


def test_sections_compose_in_order(qtbot: QtBot) -> None:
    """Zakładki z ``tabs`` + dołożone HTML/Markdown zachowują kolejność dołożenia."""
    window = HelpWindow(tabs=[("A", "<p>a</p>")])
    qtbot.addWidget(window)
    window.add_markdown_section("B", "# b")
    window.add_html_section("C", "<p>c</p>")

    tabs = _tab_widget(window)
    assert [tabs.tabText(i) for i in range(tabs.count())] == ["A", "B", "C"]
    assert [markdown for _b, _c, markdown in window._browsers] == [False, True, False]


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


def test_code_escapes_content() -> None:
    """Helper treści: ``code`` escapuje tekst (granica zaufania → setHtml)."""
    out = help_html.code("a < b & c")
    assert "a &lt; b &amp; c" in out
    # Surowy znacznik nie może przeciec do HTML.
    assert "a < b" not in out
    assert "<code" in out  # własne znaczniki helpera zostają


def test_preformatted_escapes_content() -> None:
    """Helper treści: ``preformatted`` escapuje listing (np. przekierowania powłoki)."""
    out = help_html.preformatted("grep x <in >out & tail")
    assert "grep x &lt;in &gt;out &amp; tail" in out
    assert "<in" not in out.replace("<pre", "")  # tylko własny <pre>, nie treść


def test_table_escapes_headers_and_cells() -> None:
    """Helper treści: nagłówki i komórki tabeli są escapowane jako dane."""
    out = help_html.table(["a & b"], [["x < y"]])
    assert ">a &amp; b</th>" in out
    assert ">x &lt; y</td>" in out


def test_structure_helpers_do_not_escape_composed_html() -> None:
    """Helpery struktury składają zaufany HTML — NIE escapują (kontrakt kompozycji)."""
    # paragraph/section/unordered_list przepuszczają zagnieżdżony HTML bez zmian.
    assert help_html.paragraph(help_html.code("ls")) == f"<p>{help_html.code('ls')}</p>"
    assert help_html.section("T", "<p>x</p>") == "<h3>T</h3><p>x</p>"
    assert help_html.unordered_list("<b>a</b>") == "<ul><li><b>a</b></li></ul>"
