"""Okno pomocy z zakładkami (warstwa ``qt/widgets``) — wyniesione z pdf2md.

Treść jest WSTRZYKIWANA jako lista ``(tytuł, html)`` przez parametr ``tabs`` —
okno nie zna żadnej konkretnej aplikacji ani jej tematów pomocy. Zakładki HTML składa
się helperami z :mod:`chodzkos_gui_kit.qt.widgets.help_html` (kolory przez
``palette(...)``, zero hexów).

Zakładki MARKDOWN: obok zakładek HTML można dołożyć zakładkę renderowaną z Markdown
(:meth:`HelpWindow.add_markdown_section`) — treść w pamięci albo z pliku (``str | Path``,
plik czytany przy dołożeniu). Render przez natywne ``QTextBrowser.setMarkdown`` (CommonMark
+ tabele/bloki kodu), bez zewnętrznych zależności. To umożliwia „jeden plik prawdy": aplikacja
podaje ścieżkę do swojego ``docs/*.md``, a nie duplikuje treści w kodzie.

Re-render przy zmianie motywu (subtelne): ``QTextBrowser.setHtml``/``setMarkdown`` rozwiązuje
kolory (``palette(...)`` w HTML, paleta widgetu w Markdown) do konkretnych wartości przy KAŻDYM
wywołaniu, a ``QTextDocument`` ich potem nie aktualizuje. Dlatego :meth:`HelpWindow.changeEvent`
na ``PaletteChange`` renderuje treść PONOWNIE tą samą metodą (``setHtml`` dla HTML, ``setMarkdown``
dla Markdown) z TĄ SAMĄ treścią — nie regenerujemy jej, tylko każemy Qt rozwiązać kolory od nowa.
Okno jest self-contained (zdarzenie Qt, bez ``ThemeManager``).

i18n: okno nie ma własnych etykiet poza tytułem (parametr) — przycisk „Close" to
standardowy :class:`QDialogButtonBox`, tłumaczony przez ``QTranslator`` Qt. Treść
zakładek to parametr ``tabs`` / metody ``add_*_section``.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QScrollArea,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from chodzkos_gui_kit.qt.theme import current_palette, mode_of
from chodzkos_gui_kit.qt.titlebar import TitlebarSync


def _scroll(widget: QWidget) -> QScrollArea:
    """Owija widget w przewijalny obszar (treść pomocy bywa dłuższa niż okno)."""
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setWidget(widget)
    return area


class HelpWindow(QDialog):
    """Okno pomocy z zakładkami wstrzykiwanymi jako ``(tytuł, html)``.

    Args:
        parent: okno-rodzic (zwykle główne okno aplikacji).
        title: tytuł okna (np. „Pomoc — pdf2md"). Domyślnie ``"Help"``.
        tabs: lista ``(tytuł_zakładki, html)``. HTML zawiera literalne
            ``palette(...)`` (składany helperami z :mod:`.help_html`) — re-render
            na ``PaletteChange`` rozwiązuje je do bieżącego motywu. ``None`` →
            okno bez zakładek. Zakładki Markdown/HTML można też dołożyć po konstrukcji
            (:meth:`add_markdown_section` / :meth:`add_html_section`) — do przeplatania
            w wybranej kolejności.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        title: str = "Help",
        tabs: list[tuple[str, str]] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        # Tylko rozmiar startowy — geometrii NIE persystujemy (kit nie narzuca
        # QSettings ani configu; okno startuje w rozmiarze domyślnym).
        self.resize(720, 560)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # (browser, treść, markdown?) — źródło do przemalowania przy zmianie motywu:
        # setHtml/setMarkdown zamraża kolory, więc po zmianie palety re-renderujemy.
        self._browsers: list[tuple[QTextBrowser, str, bool]] = []
        self._tabs = QTabWidget()
        for tab_title, html in tabs or []:
            self._add_tab(tab_title, html, markdown=False)
        layout.addWidget(self._tabs)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Ciemna/jasna belka tytułu podążająca za motywem aplikacji (DWM). Motyw
        # czytamy leniwie z current_palette — TitlebarSync zostaje dzieckiem okna.
        self._titlebar = TitlebarSync(self, lambda: mode_of(current_palette()))
        self._titlebar.refresh()

    def _add_tab(self, title: str, content: str, *, markdown: bool) -> None:
        """Dokłada zakładkę (HTML albo Markdown) i rejestruje ją do re-renderu motywu."""
        browser = QTextBrowser()
        if markdown:
            browser.setMarkdown(content)
        else:
            browser.setHtml(content)
        self._browsers.append((browser, content, markdown))
        self._tabs.addTab(_scroll(browser), title)

    def add_html_section(self, title: str, html: str) -> None:
        """Dokłada zakładkę HTML (jak wpis ``tabs``) — do kompozycji w zadanej kolejności.

        Równoważne wpisowi ``(title, html)`` w ``tabs``, ale wołane po konstrukcji — pozwala
        przeplatać zakładki HTML i Markdown w wybranej kolejności bez zmiany kontraktu ``tabs``.
        """
        self._add_tab(title, html, markdown=False)

    def add_markdown_section(self, title: str, source: str | Path) -> None:
        """Dokłada zakładkę renderowaną z Markdown (``QTextBrowser.setMarkdown``).

        ``source`` to treść Markdown (``str``) albo ścieżka do pliku (``Path``, czytany przy
        dołożeniu, UTF-8). Umożliwia „jeden plik prawdy": konsument podaje ścieżkę do swojego
        ``docs/*.md`` zamiast duplikować treść w kodzie. Kolory podążają za motywem — re-render
        na ``PaletteChange`` (patrz :meth:`changeEvent`).
        """
        text = source.read_text(encoding="utf-8") if isinstance(source, Path) else source
        self._add_tab(title, text, markdown=True)

    def changeEvent(self, event: QEvent) -> None:  # noqa: N802 — Qt API
        """Przemalowuje treść zakładek po zmianie palety (motywu).

        Kolory są rozwiązywane do konkretnych wartości przy ``setHtml``/``setMarkdown`` i NIE
        aktualizują się same przy zmianie motywu — więc na ``PaletteChange`` renderujemy ponownie
        tą samą metodą i tą samą treścią (Qt rozwiązuje kolory od nowa, bieżącą paletą).
        """
        if event.type() == QEvent.Type.PaletteChange:
            for browser, content, markdown in self._browsers:
                if markdown:
                    browser.setMarkdown(content)
                else:
                    browser.setHtml(content)
        super().changeEvent(event)
