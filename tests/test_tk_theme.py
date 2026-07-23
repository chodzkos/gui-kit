"""Testy toru tkinter — logika bez wyświetlacza (mapowanie palety, auto, titlebar).

Testy wymagające żywego roota Tk oznaczono ``@pytest.mark.tk`` (pomijane domyślnie
jak ``windows``). PySide6 NIE jest tu wymagany.
"""

from __future__ import annotations

import ctypes
from types import SimpleNamespace

import pytest

from chodzkos_gui_kit.palette import DARK, LIGHT, Palette
from chodzkos_gui_kit.tk import theme as tk_theme
from chodzkos_gui_kit.tk import titlebar


@pytest.mark.parametrize("palette", [DARK, LIGHT])
def test_palette_colors_mirrors_palette_fields(palette: Palette) -> None:
    """palette_colors to wierne odwzorowanie pól palety (zero własnych hexów)."""
    colors = tk_theme.palette_colors(palette)
    for field, value in colors.items():
        assert value == getattr(palette, field), f"{palette.name}.{field}"
    # kluczowe role i stany pochodne są obecne
    assert colors["bg"] == palette.bg
    assert colors["selection_bg"] == palette.selection_bg
    assert colors["focus_border"] == palette.focus_border


@pytest.mark.parametrize("palette", [DARK, LIGHT])
def test_widget_options_map_roles_to_palette(palette: Palette) -> None:
    """widget_options mapuje klasy Tk na właściwe role palety (czysta logika)."""
    assert tk_theme.widget_options("Tk", palette) == {"bg": palette.bg}
    assert tk_theme.widget_options("Frame", palette) == {"bg": palette.bg2}
    listbox = tk_theme.widget_options("Listbox", palette)
    assert listbox["selectbackground"] == palette.selection_bg
    assert listbox["selectforeground"] == palette.selection_fg
    assert listbox["bg"] == palette.bg3
    entry = tk_theme.widget_options("Entry", palette)
    assert entry["insertbackground"] == palette.accent
    # klasa obsługiwana w pełni przez ttk / nieznana → brak nadpisań
    assert tk_theme.widget_options("TButton", palette) == {}
    assert tk_theme.widget_options("Spinbox", palette) == {}


def test_system_scheme_maps_darkdetect(monkeypatch: pytest.MonkeyPatch) -> None:
    """system_scheme: Light→light, Dark→dark, None/brak→dark (reguła Unknown→dark)."""
    for value, expected in (("Light", "light"), ("Dark", "dark"), (None, "dark")):
        monkeypatch.setattr(tk_theme, "_darkdetect", SimpleNamespace(theme=lambda v=value: v))
        assert tk_theme.system_scheme() == expected
    # darkdetect niezainstalowany → dark
    monkeypatch.setattr(tk_theme, "_darkdetect", None)
    assert tk_theme.system_scheme() == "dark"


def test_resolve_name_and_palette_for(monkeypatch: pytest.MonkeyPatch) -> None:
    """auto rozwiązuje motyw przez system_scheme; light/dark wprost."""
    monkeypatch.setattr(tk_theme, "system_scheme", lambda: "light")
    assert tk_theme.resolve_name("auto") == "light"
    assert tk_theme.palette_for("auto") is LIGHT
    monkeypatch.setattr(tk_theme, "system_scheme", lambda: "dark")
    assert tk_theme.resolve_name("auto") == "dark"
    assert tk_theme.resolve_name("light") == "light"
    assert tk_theme.palette_for("dark") is DARK


def test_mode_of_narrows_palette_name() -> None:
    """mode_of zwraca ThemeName z palety."""
    assert tk_theme.mode_of(DARK) == "dark"
    assert tk_theme.mode_of(LIGHT) == "light"


def test_sync_titlebar_maps_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """sync_titlebar mapuje motyw na flagę (dark→True, light→False)."""
    calls: list[bool] = []
    monkeypatch.setattr(titlebar, "set_titlebar_dark", lambda _w, dark: calls.append(dark))
    dummy = object()
    titlebar.sync_titlebar(dummy, "dark")  # type: ignore[arg-type]
    titlebar.sync_titlebar(dummy, "light")  # type: ignore[arg-type]
    assert calls == [True, False]


def test_configure_getparent_uses_pointer_sized_handle() -> None:
    """GetParent.argtypes/restype = typ WSKAŹNIKOWY — łapie truncację 64-bit HWND (v2.9).

    Wstrzykujemy ``c_void_p`` (na Windows ``wintypes.HWND`` jest mu równe), więc test
    działa bez Windows i bez ``ctypes.wintypes`` — tak jak dwm._configure_signatures.
    """
    user32 = SimpleNamespace(GetParent=SimpleNamespace())

    titlebar._configure_getparent(user32, ctypes.c_void_p)

    # Argument (winfo_id) marshalowany jako wskaźnik — bez tego 64-bit HWND się utnie.
    assert user32.GetParent.argtypes == (ctypes.c_void_p,)
    # restype wskaźnikowy — bez tego bit 31 uchwytu wracałby jako liczba ujemna.
    assert user32.GetParent.restype is ctypes.c_void_p


def test_set_titlebar_dark_noop_off_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    """Poza Windows set_titlebar_dark nie woła winutil.dwm (winfo_id ≠ HWND)."""
    monkeypatch.setattr(titlebar.sys, "platform", "linux")
    called: list[tuple[int, bool]] = []
    monkeypatch.setattr(titlebar.dwm, "set_titlebar", lambda h, d: called.append((h, d)))
    titlebar.set_titlebar_dark(object(), True)  # type: ignore[arg-type]
    assert called == []


@pytest.mark.windows
def test_set_titlebar_dark_calls_dwm_on_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    """Na Windows set_titlebar_dark wyłuskuje HWND i woła winutil.dwm.set_titlebar."""
    monkeypatch.setattr(titlebar.sys, "platform", "win32")
    monkeypatch.setattr(titlebar, "_window_hwnd", lambda _w: 4242)
    calls: list[tuple[int, bool]] = []
    monkeypatch.setattr(titlebar.dwm, "set_titlebar", lambda h, d: calls.append((h, d)))
    titlebar.set_titlebar_dark(object(), True)  # type: ignore[arg-type]
    assert calls == [(4242, True)]


@pytest.mark.tk
def test_apply_theme_on_live_root_colors_widgets() -> None:
    """apply_theme na żywym roocie Tk koloruje widgety i ustawia current_palette."""
    import tkinter as tk

    root = tk.Tk()
    try:
        frame = tk.Frame(root)
        frame.pack()
        listbox = tk.Listbox(frame)
        listbox.pack()

        tk_theme.apply_theme(root, DARK)

        assert tk_theme.current_palette() is DARK
        assert str(root.cget("bg")) == DARK.bg
        assert str(frame.cget("bg")) == DARK.bg2
        assert str(listbox.cget("selectbackground")) == DARK.selection_bg
    finally:
        root.destroy()
