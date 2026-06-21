"""Warstwa 2b — tor tkinter: motyw i pasek tytułu (kolory z palette, DWM z winutil).

``tk`` importuje tkinter i NIE importuje PySide6 (i odwrotnie). Pasek tytułu
korzysta z tego samego ``winutil.dwm`` co tor Qt.
"""

from chodzkos_gui_kit.tk.theme import (
    ThemeManager,
    ThemeName,
    ThemeSetting,
    apply_theme,
    current_palette,
    mode_of,
    palette_colors,
    palette_for,
    resolve_name,
    system_scheme,
    widget_options,
)
from chodzkos_gui_kit.tk.titlebar import set_titlebar_dark, sync_titlebar

__all__ = [
    "ThemeManager",
    "ThemeName",
    "ThemeSetting",
    "apply_theme",
    "current_palette",
    "mode_of",
    "palette_colors",
    "palette_for",
    "resolve_name",
    "set_titlebar_dark",
    "sync_titlebar",
    "system_scheme",
    "widget_options",
]
