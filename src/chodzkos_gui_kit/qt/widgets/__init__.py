"""Wspólne widgety Qt wielokrotnego użytku (warstwa ``qt/widgets``).

Widgety odsprzężone od aplikacji: config przez ``DialogConfig``
(``MutableMapping``), i18n przez parametry tekstowe z angielskimi domyślnymi.
"""

from __future__ import annotations

from chodzkos_gui_kit.qt.widgets.about import AboutPanel, AboutTexts
from chodzkos_gui_kit.qt.widgets.file_list import FileList, FileListTexts
from chodzkos_gui_kit.qt.widgets.help_html import (
    code,
    paragraph,
    preformatted,
    section,
    table,
    unordered_list,
)
from chodzkos_gui_kit.qt.widgets.help_window import HelpWindow
from chodzkos_gui_kit.qt.widgets.log_view import LogView
from chodzkos_gui_kit.qt.widgets.path_entry import (
    FileTypes,
    PathEntry,
    PathEntryTexts,
    PathMode,
)
from chodzkos_gui_kit.qt.widgets.scroll import make_scrollable

__all__ = [
    "AboutPanel",
    "AboutTexts",
    "FileList",
    "FileListTexts",
    "FileTypes",
    "HelpWindow",
    "LogView",
    "PathEntry",
    "PathEntryTexts",
    "PathMode",
    "code",
    "make_scrollable",
    "paragraph",
    "preformatted",
    "section",
    "table",
    "unordered_list",
]
