"""Wspólne ustawienia testów toru Qt (PySide6 / pytest-qt).

Wymusza platformę ``offscreen`` (brak displaya w CI) jeszcze zanim pytest-qt
utworzy ``QApplication`` — ustawienie zmiennej środowiskowej na poziomie importu
modułu wykonuje się w fazie zbierania testów, przed pierwszym użyciem fixture.
Nie importujemy tu PySide6, żeby testy warstwy 0 (palette, config) działały bez
zainstalowanego Qt.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
