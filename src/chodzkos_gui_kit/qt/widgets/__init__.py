"""Wspólne widgety Qt wielokrotnego użytku (warstwa ``qt/widgets``).

Widgety odsprzężone od aplikacji: config przez ``DialogConfig``
(``MutableMapping``), i18n przez parametry tekstowe z angielskimi domyślnymi.
"""

from __future__ import annotations

from chodzkos_gui_kit.qt.widgets.path_entry import (
    FileTypes,
    PathEntry,
    PathEntryTexts,
    PathMode,
)

__all__ = ["FileTypes", "PathEntry", "PathEntryTexts", "PathMode"]
