"""Warstwa 2a — tor Qt (PySide6): motyw, pasek tytułu, dialogi plików.

Zależności wewnętrzne: ``theme`` używa ``titlebar`` (DWM przez ``winutil``),
``dialogs`` używa obu. ``titlebar`` nie importuje ``theme`` w czasie wykonania
(tylko ``TYPE_CHECKING``), więc kolejność importów tu nie tworzy cyklu.
"""

from chodzkos_gui_kit.qt.dialogs import (
    open_file,
    open_files,
    pick_dir,
    save_file,
    use_native_dialog,
)
from chodzkos_gui_kit.qt.icons import ICON_MAP, clear_cache, get_icon
from chodzkos_gui_kit.qt.theme import (
    ThemeManager,
    ThemeName,
    ThemeSetting,
    apply_theme,
    build_palette,
    build_qss,
    current_palette,
    mode_of,
    set_current_palette,
    system_scheme,
)
from chodzkos_gui_kit.qt.titlebar import TitlebarSync, set_titlebar_dark, sync_titlebar

__all__ = [
    "ICON_MAP",
    "ThemeManager",
    "ThemeName",
    "ThemeSetting",
    "TitlebarSync",
    "apply_theme",
    "build_palette",
    "build_qss",
    "clear_cache",
    "current_palette",
    "get_icon",
    "mode_of",
    "open_file",
    "open_files",
    "pick_dir",
    "save_file",
    "set_current_palette",
    "set_titlebar_dark",
    "sync_titlebar",
    "system_scheme",
    "use_native_dialog",
]
