"""Okno pomocy z zakładkami (warstwa ``qt/widgets``) — wyniesione z pdf2md.

Treść jest WSTRZYKIWANA jako lista ``(tytuł, html)`` przez parametr ``tabs`` —
okno nie zna żadnej konkretnej aplikacji ani jej tematów pomocy. Zakładki składa
się helperami z :mod:`chodzkos_gui_kit.qt.widgets.help_html` (kolory przez
``palette(...)``, zero hexów).

Re-render przy zmianie motywu (subtelne): ``QTextBrowser.setHtml`` rozwiązuje
``palette(...)`` do konkretnych kolorów przy KAŻDYM wywołaniu z bieżącą paletą, a
``QTextDocument`` ich potem nie aktualizuje. Dlatego :meth:`HelpWindow.changeEvent`
na ``PaletteChange`` woła ``setHtml`` PONOWNIE z TYM SAMYM html — nie regenerujemy
treści, tylko każemy Qt rozwiązać ``palette(...)`` od nowa. Stąd statyczna lista
``tabs`` wystarcza (factory zbędne), a okno jest self-contained (zdarzenie Qt, bez
``ThemeManager``).

i18n: okno nie ma własnych etykiet poza tytułem (parametr) — przycisk „Close" to
standardowy :class:`QDialogButtonBox`, tłumaczony przez ``QTranslator`` Qt. Treść
zakładek to parametr ``tabs``.
"""

from __future__ import annotations

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
            okno bez zakładek.
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

        # (browser, html) — źródło do przemalowania przy zmianie motywu: setHtml
        # zamraża kolory palette(...), więc po zmianie palety re-renderujemy.
        self._browsers: list[tuple[QTextBrowser, str]] = []
        tab_widget = QTabWidget()
        for tab_title, html in tabs or []:
            browser = QTextBrowser()
            browser.setHtml(html)
            self._browsers.append((browser, html))
            tab_widget.addTab(_scroll(browser), tab_title)
        layout.addWidget(tab_widget)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Ciemna/jasna belka tytułu podążająca za motywem aplikacji (DWM). Motyw
        # czytamy leniwie z current_palette — TitlebarSync zostaje dzieckiem okna.
        self._titlebar = TitlebarSync(self, lambda: mode_of(current_palette()))
        self._titlebar.refresh()

    def changeEvent(self, event: QEvent) -> None:  # noqa: N802 — Qt API
        """Przemalowuje treść zakładek po zmianie palety (motywu).

        ``palette(...)`` w HTML jest rozwiązywane do konkretnych kolorów przy
        ``setHtml`` i NIE aktualizuje się samo przy zmianie motywu — więc na
        ``PaletteChange`` wołamy ``setHtml`` ponownie z tym samym html (Qt
        rozwiązuje ``palette(...)`` od nowa, bieżącą paletą).
        """
        if event.type() == QEvent.Type.PaletteChange:
            for browser, html in self._browsers:
                browser.setHtml(html)
        super().changeEvent(event)
