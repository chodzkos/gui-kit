"""Testy własnego silnika motywu (Fusion + QPalette + QSS akcenty)."""

from __future__ import annotations

import pytest
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QTableWidget, QTableWidgetItem, QToolTip, QWidget

from chodzkos_gui_kit.palette import DARK, LIGHT, Palette
from chodzkos_gui_kit.qt import theme as theme_mod
from chodzkos_gui_kit.qt.theme import (
    ThemeManager,
    apply_theme,
    build_qss,
    current_palette,
)

pytestmark = pytest.mark.qt


def test_apply_dark_sets_fusion_palette_and_states(qapp: QApplication) -> None:
    """Ciemny: styl Fusion, role bazowe i grupa Disabled wg §5."""
    config: dict[str, object] = {}
    manager = ThemeManager(qapp, config)

    emitted: list[object] = []
    manager.theme_changed.connect(emitted.append)
    manager.apply("dark")

    # Po setStyleSheet styl jest opakowany w QStyleSheetStyle — czyszcząc QSS
    # odsłaniamy styl bazowy, który MUSI być Fusion (§4).
    palette = qapp.palette()
    qapp.setStyleSheet("")
    assert "fusion" in qapp.style().metaObject().className().lower()
    role = QPalette.ColorRole
    group = QPalette.ColorGroup
    # QColor.name() zwraca hex małymi literami — porównujemy bez wielkości liter.
    assert palette.color(role.Window).name() == DARK.bg.lower()
    assert palette.color(role.Base).name() == DARK.bg3.lower()
    assert palette.color(role.Highlight).name() == DARK.selection_bg.lower()
    assert palette.color(role.PlaceholderText).name() == DARK.placeholder.lower()
    assert palette.color(group.Disabled, role.WindowText).name() == DARK.disabled_fg.lower()
    # Rola Link = accent_text (w ciemnym motywie = accent marki).
    assert palette.color(role.Link).name() == DARK.accent_text.lower()

    assert manager.setting == "dark"
    assert manager.palette == DARK
    assert config["theme"] == "dark"
    assert current_palette() == DARK
    assert emitted == [DARK]


def test_apply_light_link_meets_wcag(qapp: QApplication) -> None:
    """Jasny: tło białe, a link to ciemniejszy accent2 (nota kontrastu WCAG §5)."""
    manager = ThemeManager(qapp, {})
    manager.apply("light")

    palette = qapp.palette()
    role = QPalette.ColorRole
    assert palette.color(role.Window).name() == LIGHT.bg.lower()
    # Link = accent_text; w jasnym motywie to ciemniejszy accent2 (>=4.5:1, §5).
    assert palette.color(role.Link).name() == LIGHT.accent_text.lower()
    assert LIGHT.accent_text == LIGHT.accent2
    assert manager.palette == LIGHT
    assert current_palette() == LIGHT


@pytest.mark.parametrize("palette", [DARK, LIGHT])
def test_qss_has_no_base_palette_hexes(palette: Palette) -> None:
    """QSS niesie tylko akcenty — kolorów bazowych z palety w nim nie ma (§4)."""
    qss = build_qss(palette)
    for hex_value in (palette.bg, palette.bg2, palette.bg3, palette.fg, palette.fg2, palette.fg3):
        assert hex_value not in qss, f"QSS dubluje kolor bazowy {hex_value}"


def test_system_scheme_maps_unknown_to_dark(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    """system_scheme: Light→light, Dark/Unknown→dark (fallback dla Linux bez XDG)."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QGuiApplication

    class _FakeHints:
        def __init__(self, scheme: Qt.ColorScheme) -> None:
            self._scheme = scheme

        def colorScheme(self) -> Qt.ColorScheme:  # noqa: N802 — Qt API
            return self._scheme

    for scheme, expected in (
        (Qt.ColorScheme.Light, "light"),
        (Qt.ColorScheme.Dark, "dark"),
        (Qt.ColorScheme.Unknown, "dark"),
    ):
        monkeypatch.setattr(
            QGuiApplication, "styleHints", staticmethod(lambda s=scheme: _FakeHints(s))
        )
        assert theme_mod.system_scheme() == expected


def test_auto_maps_system_scheme(qapp: QApplication, monkeypatch: pytest.MonkeyPatch) -> None:
    """Tryb auto rozwiązuje motyw z motywu systemu (Dark/Light)."""
    manager = ThemeManager(qapp, {})
    monkeypatch.setattr(theme_mod, "system_scheme", lambda: "dark")
    assert manager.resolved_name("auto") == "dark"
    monkeypatch.setattr(theme_mod, "system_scheme", lambda: "light")
    assert manager.resolved_name("auto") == "light"


def test_colorscheme_subscription_only_in_auto(qapp: QApplication) -> None:
    """colorSchemeChanged podłączony tylko w trybie auto, odłączany przy wymuszeniu."""
    manager = ThemeManager(qapp, {})
    manager.apply("auto")
    assert manager._auto_connection is not None
    manager.apply("dark")
    assert manager._auto_connection is None
    manager.apply("auto")
    assert manager._auto_connection is not None


def test_initial_setting_read_from_config(qapp: QApplication) -> None:
    """Ustawienie startowe pochodzi z configu (domyślnie auto przy złej wartości)."""
    assert ThemeManager(qapp, {"theme": "dark"}).setting == "dark"
    assert ThemeManager(qapp, {"theme": "śmieci"}).setting == "auto"
    assert ThemeManager(qapp, {}).setting == "auto"


def test_apply_theme_repolishes_without_error(qapp: QApplication) -> None:
    """apply_theme stosuje motyw bez wyjątku (Fusion + paleta + QSS + repolish)."""
    apply_theme(qapp, LIGHT)
    assert qapp.styleSheet() != ""
    apply_theme(qapp, DARK)
    assert qapp.styleSheet() != ""
    qapp.setStyleSheet("")  # odsłoń styl bazowy
    assert "fusion" in qapp.style().metaObject().className().lower()


def test_tooltip_palette_and_qss_refresh_on_runtime_theme_switch(qapp: QApplication) -> None:
    """Tooltip i QSS dostają świeże kolory przy zmianie motywu w locie (regresja v2.3)."""
    manager = ThemeManager(qapp, {})
    role = QPalette.ColorRole

    manager.apply("dark")
    assert QToolTip.palette().color(role.ToolTipBase).name() == DARK.bg2.lower()
    assert QToolTip.palette().color(role.ToolTipText).name() == DARK.fg.lower()

    manager.apply("light")
    light_qss = qapp.styleSheet().lower()
    assert QToolTip.palette().color(role.ToolTipBase).name() == LIGHT.bg2.lower()
    assert QToolTip.palette().color(role.ToolTipText).name() == LIGHT.fg.lower()
    assert DARK.bg2.lower() not in light_qss
    assert DARK.fg.lower() not in light_qss

    manager.apply("dark")
    dark_qss = qapp.styleSheet().lower()
    assert QToolTip.palette().color(role.ToolTipBase).name() == DARK.bg2.lower()
    assert QToolTip.palette().color(role.ToolTipText).name() == DARK.fg.lower()
    assert LIGHT.bg2.lower() not in dark_qss
    assert LIGHT.fg.lower() not in dark_qss


def test_attach_titlebar_syncs_on_apply(
    qapp: QApplication, qtbot, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Dołączone okno dostaje DWM = motyw app przy każdym apply() (bezwarunkowo)."""
    from PySide6.QtWidgets import QWidget

    from chodzkos_gui_kit.qt import titlebar

    calls: list[bool] = []
    monkeypatch.setattr(titlebar.dwm, "set_titlebar", lambda _hwnd, dark: calls.append(dark))

    window = QWidget()
    qtbot.addWidget(window)
    manager = ThemeManager(qapp, {})
    manager.attach_titlebar(window)  # natychmiastowy sync (paleta startowa = dark)

    # apply() odracza przemalowanie belki o cykl pętli zdarzeń (singleShot, fix Win11),
    # więc spinujemy pętlę MIĘDZY zmianami — tak jak w realnym użyciu (zmiany motywu
    # są rozdzielone w czasie). Bez tego oba odroczenia odczytałyby już finalny motyw.
    manager.apply("light")
    qtbot.wait(20)
    manager.apply("dark")
    qtbot.wait(20)
    # attach (dark) + apply(light) + apply(dark) → ostatnia wartość to dark=True.
    assert calls[-1] is True
    assert False in calls and True in calls


def test_repolish_repaints_item_views_on_theme_switch(qapp: QApplication) -> None:
    """QAbstractItemView dostaje świeżą paletę po dark→light (nie zostaje stary Base)."""
    role = QPalette.ColorRole
    table = QTableWidget(1, 1)
    table.setItem(0, 0, QTableWidgetItem("x"))

    apply_theme(qapp, DARK)
    assert table.palette().color(role.Base).name() == DARK.bg3.lower()

    apply_theme(qapp, LIGHT)
    # Bez repaintu item-view zostałby DARK.bg3 — fix wymusza LIGHT.bg3.
    assert table.palette().color(role.Base).name() == LIGHT.bg3.lower()


def test_repolish_does_not_touch_non_item_views(qapp: QApplication) -> None:
    """Celowanie: zwykły widget z WŁASNĄ paletą nie jest nadpisany (tylko item-views)."""
    widget = QWidget()
    custom = QPalette()
    custom.setColor(QPalette.ColorRole.Base, QColor(1, 2, 3))
    widget.setPalette(custom)

    apply_theme(qapp, LIGHT)

    assert widget.palette().color(QPalette.ColorRole.Base) == QColor(1, 2, 3)


def test_apply_theme_repaint_item_views_can_be_disabled(qapp: QApplication) -> None:
    """Flaga repaint_item_views=False NIE nadpisuje palety item-view (własna obsługa)."""
    table = QTableWidget(1, 1)
    custom = QPalette()
    custom.setColor(QPalette.ColorRole.Base, QColor(1, 2, 3))
    table.setPalette(custom)

    apply_theme(qapp, DARK, repaint_item_views=False)

    # Z wyłączoną flagą sentinel zostaje (dowód, że flaga steruje ścieżką item-views).
    assert table.palette().color(QPalette.ColorRole.Base) == QColor(1, 2, 3)
