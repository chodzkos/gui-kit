"""Motyw aplikacji tkinter — paleta z kitu + rekurencyjne kolorowanie (§3, §5).

Tor tkinter równoległy do ``qt/theme.py``: te same role/stany z
:mod:`chodzkos_gui_kit.palette` (ZERO lokalnych hexów), to samo API
``ThemeManager.apply(setting)``. Różnice wynikają z toolkitu:

* zamiast ``QPalette``/QSS — ``ttk.Style`` (styl ``clam``) + rekurencyjne
  ``configure`` na klasycznych widgetach (Listbox/Text/Canvas same nie słuchają
  ttk — pułapka z §3);
* auto-detekcja przez ``darkdetect`` (tkinter nie ma ``styleHints``); wartość
  ``None``/nieznana → ``dark`` (spójnie z regułą ``Unknown → dark`` z toru Qt);
* ``darkdetect.listener`` (jeśli dostępny) działa jako wątek DAEMON i nigdy nie
  dotyka widgetów wprost — przeładowanie motywu marshalujemy na główny wątek Tk
  przez ``root.after`` (analog żelaznej zasady wątków z toru Qt).

Logika „rola → pole palety" jest wydzielona do czystych funkcji
(:func:`palette_colors`, :func:`widget_options`) testowalnych BEZ wyświetlacza;
samo ``apply_theme`` aplikuje je na żywych widgetach (wymaga roota Tk).
"""

from __future__ import annotations

import logging
import threading
import tkinter as tk
from collections.abc import Callable, MutableMapping
from contextlib import suppress
from tkinter import ttk
from typing import Any, Literal

from chodzkos_gui_kit import palette as pal
from chodzkos_gui_kit.palette import Palette
from chodzkos_gui_kit.tk import titlebar

logger = logging.getLogger(__name__)

# darkdetect jest w extra [tk]; import zabezpieczony, by moduł dało się załadować
# bez tego rozszerzenia (np. w środowisku tylko-Qt). Brak → auto traktuje jak dark.
try:
    import darkdetect as _darkdetect
except ImportError:  # pragma: no cover - zależy od środowiska
    _darkdetect = None

ThemeSetting = Literal["auto", "light", "dark"]
ThemeName = Literal["dark", "light"]

_THEME_SETTINGS: tuple[ThemeSetting, ...] = ("auto", "light", "dark")

# Klucz ustawienia motywu w configu (wspólny z torem Qt).
THEME_KEY = "theme"

# Role/stany palety, które tkinter konsumuje jako napisy-kolory (bridge do świata
# stringów Tk). Jedyne źródło wartości to Palette — tu tylko nazwy pól.
_ROLE_FIELDS: tuple[str, ...] = (
    "bg",
    "bg2",
    "bg3",
    "fg",
    "fg2",
    "fg3",
    "accent",
    "accent2",
    "border",
    "red",
    "amber",
    "hover",
    "pressed",
    "selection_bg",
    "selection_fg",
    "disabled_fg",
    "disabled_bg",
    "placeholder",
    "focus_border",
)

# Bieżąca paleta — odczytywana przez widgety budowane dynamicznie (tooltipy itp.).
_current: Palette = pal.DARK


def current_palette() -> Palette:
    """Zwraca ostatnio zastosowaną paletę (domyślnie DARK przed pierwszym apply)."""
    return _current


def mode_of(palette: Palette) -> ThemeName:
    """Zwraca motyw palety jako ``ThemeName`` (zawęża ``Palette.name: str``)."""
    return "light" if palette.name == "light" else "dark"


def system_scheme() -> ThemeName:
    """Motyw systemu przez ``darkdetect`` (``None``/brak/nieznane → dark).

    Spójne z regułą ``Unknown → dark`` z toru Qt: ciemny jest motywem
    podstawowym, więc każda niepewność wpada w dark.
    """
    if _darkdetect is None:
        return "dark"
    name = (_darkdetect.theme() or "").lower()
    return "light" if name == "light" else "dark"


def resolve_name(setting: ThemeSetting) -> ThemeName:
    """Mapuje ustawienie na konkretny motyw (``auto`` → motyw systemu)."""
    if setting == "auto":
        return system_scheme()
    return "light" if setting == "light" else "dark"


def palette_for(setting: ThemeSetting) -> Palette:
    """Zwraca paletę dla ustawienia (``auto`` rozwiązany przez motyw systemu)."""
    return pal.get(resolve_name(setting))


def palette_colors(palette: Palette) -> dict[str, str]:
    """Spłaszcza paletę do słownika ``rola → hex`` (forma, której używa tkinter).

    Most między :class:`Palette` a światem napisów-kolorów Tk; jedyne źródło
    wartości to pola palety (zero hexów tutaj).
    """
    return {field: getattr(palette, field) for field in _ROLE_FIELDS}


def widget_options(class_name: str, palette: Palette) -> dict[str, str]:
    """Zwraca opcje ``configure`` dla klasycznego widgetu danej klasy Tk.

    Czysta funkcja (bez Tk) — mapuje ``winfo_class()`` na role palety. Klasy
    obsługiwane przez ttk.Style albo nieznane → pusty słownik. Testowalna bez
    wyświetlacza.
    """
    if class_name in {"Tk", "Toplevel"}:
        return {"bg": palette.bg}
    if class_name in {"Frame", "Labelframe"}:
        return {"bg": palette.bg2}
    if class_name == "Label":
        return {"bg": palette.bg2, "fg": palette.fg}
    if class_name == "Button":
        return {"bg": palette.bg3, "fg": palette.fg, "activebackground": palette.hover}
    if class_name in {"Entry", "Text"}:
        return {"bg": palette.bg3, "fg": palette.fg, "insertbackground": palette.accent}
    if class_name == "Listbox":
        return {
            "bg": palette.bg3,
            "fg": palette.fg,
            "selectbackground": palette.selection_bg,
            "selectforeground": palette.selection_fg,
            "highlightbackground": palette.border,
        }
    if class_name == "Canvas":
        return {"bg": palette.bg2, "highlightbackground": palette.border}
    if class_name in {"Checkbutton", "Radiobutton"}:
        return {"bg": palette.bg2, "fg": palette.fg, "activebackground": palette.bg2}
    return {}


def apply_theme(root: tk.Misc, palette: Palette) -> None:
    """Aplikuje paletę: style ttk + rekurencyjne kolorowanie klasycznych widgetów.

    Wymaga żywego roota Tk (testy oznaczone markerem ``tk``). Aktualizuje też
    paletę modułową (:func:`current_palette`).
    """
    global _current
    _configure_ttk_style(root, palette)
    _apply_widget_theme(root, palette)
    _current = palette


def _configure_ttk_style(root: tk.Misc, palette: Palette) -> None:
    """Konfiguruje style ttk dla palety (baza + akcenty stanów)."""
    style = ttk.Style(root)
    with suppress(tk.TclError):
        style.theme_use("clam")

    style.configure(".", background=palette.bg2, foreground=palette.fg, fieldbackground=palette.bg3)
    style.configure("TFrame", background=palette.bg2)
    style.configure("Root.TFrame", background=palette.bg)
    style.configure("TLabel", background=palette.bg2, foreground=palette.fg)
    style.configure("Muted.TLabel", background=palette.bg2, foreground=palette.fg2)
    style.configure("Link.TLabel", background=palette.bg2, foreground=palette.accent_text)
    style.configure(
        "Title.TLabel",
        background=palette.bg,
        foreground=palette.fg,
        font=("TkDefaultFont", 15, "bold"),
    )
    style.configure(
        "TButton", background=palette.bg3, foreground=palette.fg, bordercolor=palette.border
    )
    style.map("TButton", background=[("active", palette.hover)])
    style.configure("TCheckbutton", background=palette.bg2, foreground=palette.fg)
    style.map("TCheckbutton", background=[("active", palette.bg2)])
    style.configure(
        "TEntry",
        fieldbackground=palette.bg3,
        foreground=palette.fg,
        insertcolor=palette.accent,
    )
    style.configure("TLabelframe", background=palette.bg2, bordercolor=palette.border)
    style.configure("TLabelframe.Label", background=palette.bg2, foreground=palette.fg)
    style.configure("TNotebook", background=palette.bg, borderwidth=0)
    style.configure("TNotebook.Tab", background=palette.bg3, foreground=palette.fg, padding=(12, 6))
    style.map("TNotebook.Tab", background=[("selected", palette.bg2)])


def _apply_widget_theme(widget: tk.Misc, palette: Palette) -> None:
    """Rekurencyjnie koloruje widgety tkinter nieobsługiwane przez ttk.Style."""
    options = widget_options(widget.winfo_class(), palette)
    if options:
        with suppress(tk.TclError):
            _configure(widget, options)
    for child in widget.winfo_children():
        _apply_widget_theme(child, palette)


def _configure(widget: tk.Misc, options: dict[str, str]) -> None:
    """Konfiguruje widget dynamicznymi opcjami tkinter (typowo niejednorodne)."""
    cast_widget: Any = widget
    cast_widget.configure(**options)


class ThemeManager:
    """Zarządza motywem aplikacji tkinter (auto/jasny/ciemny) i jego trwałością.

    API równoległe do ``qt/theme.py:ThemeManager``: :meth:`apply` przyjmuje
    ``"auto"|"light"|"dark"``, persistuje ustawienie w przekazanym ``config`` i
    aktualizuje pasek tytułu dołączonych okien (BEZWARUNKOWO, v2.5).

    Tryb ``auto`` (jeśli ``darkdetect`` wystawia ``listener``) uruchamia wątek
    DAEMON nasłuchujący zmiany motywu systemu; przeładowanie marshalujemy na
    główny wątek Tk przez ``root.after``.

    Args:
        root: główne okno/kontekst Tk (``tk.Tk`` lub dowolny ``tk.Misc``).
        config: słownik konfiguracji (``chodzkos_gui_kit.config.Config`` albo
            zwykły ``dict``) — czytany/zapisywany kluczem ``"theme"``.
    """

    def __init__(self, root: tk.Misc, config: MutableMapping[str, Any]) -> None:
        self._root = root
        self._config = config
        self._setting: ThemeSetting = self._initial_setting()
        self._palette: Palette = pal.DARK
        self._windows: list[tk.Misc] = []
        self._listener_started = False

    @property
    def setting(self) -> ThemeSetting:
        """Aktualne ustawienie trybu (auto/light/dark)."""
        return self._setting

    @property
    def palette(self) -> Palette:
        """Aktualnie zastosowana paleta."""
        return self._palette

    def _initial_setting(self) -> ThemeSetting:
        """Wczytuje ustawienie motywu z configu (domyślnie auto)."""
        value = self._config.get(THEME_KEY)
        return value if value in _THEME_SETTINGS else "auto"

    def resolved_name(self, setting: ThemeSetting | None = None) -> ThemeName:
        """Mapuje ustawienie na konkretny motyw (``auto`` → motyw systemu)."""
        return resolve_name(setting if setting is not None else self._setting)

    def apply(self, setting: ThemeSetting) -> None:
        """Ustawia tryb, zapisuje go w configu i stosuje do aplikacji."""
        self._setting = setting
        self._config[THEME_KEY] = setting
        self._palette = palette_for(setting)
        apply_theme(self._root, self._palette)
        self._sync_titlebars()
        if setting == "auto":
            self._ensure_auto_listener()

    def attach_titlebar(self, window: tk.Misc) -> None:
        """Dołącza okno do menedżera i od razu ustawia jego pasek tytułu."""
        self._windows.append(window)
        titlebar.sync_titlebar(window, mode_of(self._palette))

    def _sync_titlebars(self) -> None:
        """Ustawia pasek tytułu wszystkich dołączonych okien na motyw aplikacji."""
        mode = mode_of(self._palette)
        for window in self._windows:
            titlebar.sync_titlebar(window, mode)

    def _ensure_auto_listener(self) -> None:
        """Startuje (raz) wątek-demon ``darkdetect.listener`` dla trybu auto."""
        if self._listener_started or _darkdetect is None:
            return
        listener: Callable[[Callable[[str], None]], None] | None = getattr(
            _darkdetect, "listener", None
        )
        if listener is None:  # listener bywa niedostępny (np. część Linuksów)
            return
        self._listener_started = True
        thread = threading.Thread(target=listener, args=(self._on_system_changed,), daemon=True)
        thread.start()

    def _on_system_changed(self, _name: str) -> None:
        """Callback ``darkdetect`` (wątek listenera) — marshaluj na główny wątek Tk."""
        with suppress(tk.TclError, RuntimeError):
            self._root.after(0, self._reapply_if_auto)

    def _reapply_if_auto(self) -> None:
        """Przeładowuje motyw, jeśli wciąż jesteśmy w trybie auto (główny wątek)."""
        if self._setting == "auto":
            self.apply("auto")
