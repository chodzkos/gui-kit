"""Przewijalna powierzchnia treści (warstwa ``qt/widgets``).

:func:`make_scrollable` owija gotowy widget w pionowy, bezramkowy
``QScrollArea`` — gdy zawartość (panel ustawień, zakładka, szczegóły) przerasta
wysokość okna, pojawia się pionowy scroll, zamiast obcinać treść albo rozpychać
okno. Wyniesione z EpubForge (``make_scrollable``, ~7 zakładek); ten sam wzorzec
inline istniał w IcoForge (przewijany panel ustawień) i MediaForge (panel
szczegółów) — teraz jedno źródło.

Ważne dla motywu: ``autoFillBackground``/``WA_StyledBackground`` są wyłączone na
obszarze i viewportcie, więc tło niesie paleta aplikacji (``palette(...)`` z
motywu kitu), a nie własne tło ``QScrollArea`` — spójnie w obu motywach.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QScrollArea, QSizePolicy, QWidget


def make_scrollable(content: QWidget) -> QScrollArea:
    """Owija ``content`` w pionowy, bezramkowy ``QScrollArea`` (scroll gdy nie mieści się w oknie).

    Poziomy pasek wyłączony (treść dopasowuje szerokość do viewportu), pionowy
    pojawia się w razie potrzeby. Tło pozostawione motywowi (patrz docstring
    modułu). Zwraca ``QScrollArea`` gotowy do wstawienia w layout — ``content``
    jest już ustawiony jako jego widget.
    """
    content.setAutoFillBackground(False)
    content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setFrameShape(QFrame.Shape.NoFrame)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    area.setAcceptDrops(False)
    area.setAutoFillBackground(False)
    area.viewport().setAcceptDrops(False)
    area.viewport().setAutoFillBackground(False)
    area.viewport().setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
    area.setWidget(content)
    return area
