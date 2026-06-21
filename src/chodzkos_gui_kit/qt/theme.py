"""Motyw aplikacji Qt — własny silnik (GUI_STANDARD §4, §5).

Zamiast zewnętrznej biblioteki motywów budujemy motyw sami: styl ``Fusion``
+ :class:`QPalette` jako baza kolorów + QSS generowany WYŁĄCZNIE na akcenty.
Hexy pochodzą jedynie z :mod:`chodzkos_gui_kit.palette` — w tym module nie ma
ani jednej wartości koloru.

Kontrakt (§4, kanoniczna sekwencja v2.3):
* ``app.setStyle("Fusion")`` PRZED ``setPalette`` — natywne style Windows
  ignorują większość ról palety i zostawiają jasne kontrolki mimo ciemnej palety;
* QPalette = baza kolorów, QSS = TYLKO akcenty (ramki, zaokrąglenia, hover,
  pressed, focus, tooltip) — bez dublowania kolorów bazowych;
* QSS jest FUNKCJĄ palety (:func:`build_qss`), regenerowany przy KAŻDYM
  ``apply()`` — nigdy cache'owany string z hexami;
* sekwencja ``apply()``: ``setPalette`` → ``setStyleSheet(build_qss(...))`` →
  ``QToolTip.setPalette`` (ToolTipBase=bg2, ToolTipText=fg) →
  ``unpolish``/``polish`` + ``update()`` po ``app.allWidgets()``;
* auto-motyw przez ``styleHints().colorScheme()`` (``Unknown`` → fallback dark);
  sygnał ``colorSchemeChanged`` podłączony WYŁĄCZNIE w trybie auto.
"""

from __future__ import annotations

import logging
from collections.abc import MutableMapping
from typing import Any, Literal

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication, QPalette
from PySide6.QtWidgets import QApplication, QToolTip, QWidget

from chodzkos_gui_kit import palette as pal
from chodzkos_gui_kit.palette import Palette
from chodzkos_gui_kit.qt import titlebar

logger = logging.getLogger(__name__)

ThemeSetting = Literal["auto", "light", "dark"]
ThemeName = Literal["dark", "light"]

_THEME_SETTINGS: tuple[ThemeSetting, ...] = ("auto", "light", "dark")

# Klucz ustawienia motywu w configu.
THEME_KEY = "theme"

# Bieżąca paleta — odczytywana przez widgety budowane dynamicznie (dialogi, log).
# Ustawiana przez ThemeManager przy każdym apply().
_current: Palette = pal.DARK


def current_palette() -> Palette:
    """Zwraca ostatnio zastosowaną paletę (domyślnie DARK przed pierwszym apply)."""
    return _current


def set_current_palette(palette: Palette) -> None:
    """Ustawia paletę odczytywaną przez IconProvider (:func:`current_palette`).

    Dla konsumentów z WŁASNYM motywem (qdarktheme itp.) — pozwala przebarwić ikony
    bez przemalowania aplikacji (NIE woła ``setPalette``/``setStyleSheet``).

    NIE wołaj, jeśli używasz kitowego :class:`ThemeManager`: :func:`apply_theme`
    robi to sam, a drugie źródło zapisu rozjechałoby kolor ikon z motywem UI. To
    jedyne miejsce zapisu ``_current`` — ``apply_theme`` jest tylko jego najczęstszym
    wołającym (jedno wejście = brak rozjazdu).
    """
    global _current
    _current = palette


def mode_of(palette: Palette) -> ThemeName:
    """Zwraca motyw palety jako ``ThemeName`` (zawęża ``Palette.name: str``)."""
    return "light" if palette.name == "light" else "dark"


def system_scheme() -> ThemeName:
    """Zwraca motyw systemu z ``QStyleHints`` (``Unknown`` → fallback dark).

    ``Unknown`` zdarza się na Linuksie bez portalu XDG — traktujemy jako ciemny,
    bo ciemny jest motywem podstawowym (§4).
    """
    scheme = QGuiApplication.styleHints().colorScheme()
    return "light" if scheme == Qt.ColorScheme.Light else "dark"


def build_palette(palette: Palette) -> QPalette:
    """Buduje :class:`QPalette` z ról palety marki (baza kolorów dla Fusion).

    Rola ``Link`` używa :attr:`Palette.accent_text` (reguła kontrastu §5: w
    jasnym motywie link to ciemniejszy ``accent2``).
    """
    role = QPalette.ColorRole
    group = QPalette.ColorGroup
    qpalette = QPalette()

    qpalette.setColor(role.Window, QColor(palette.bg))
    qpalette.setColor(role.Button, QColor(palette.bg))
    qpalette.setColor(role.Base, QColor(palette.bg3))
    qpalette.setColor(role.AlternateBase, QColor(palette.bg2))
    qpalette.setColor(role.Text, QColor(palette.fg))
    qpalette.setColor(role.WindowText, QColor(palette.fg))
    qpalette.setColor(role.ButtonText, QColor(palette.fg))
    qpalette.setColor(role.PlaceholderText, QColor(palette.placeholder))
    qpalette.setColor(role.Highlight, QColor(palette.selection_bg))
    qpalette.setColor(role.HighlightedText, QColor(palette.selection_fg))
    qpalette.setColor(role.Link, QColor(palette.accent_text))
    qpalette.setColor(role.ToolTipBase, QColor(palette.bg2))
    qpalette.setColor(role.ToolTipText, QColor(palette.fg))

    # Grupa Disabled MUSI być ustawiona jawnie — inaczej Fusion wylicza własne,
    # niespójne z motywem kolory (GUI_STANDARD §5, pułapka palety).
    qpalette.setColor(group.Disabled, role.WindowText, QColor(palette.disabled_fg))
    qpalette.setColor(group.Disabled, role.Text, QColor(palette.disabled_fg))
    qpalette.setColor(group.Disabled, role.ButtonText, QColor(palette.disabled_fg))
    qpalette.setColor(group.Disabled, role.Button, QColor(palette.disabled_bg))
    qpalette.setColor(group.Disabled, role.Base, QColor(palette.disabled_bg))
    return qpalette


def build_qss(palette: Palette) -> str:
    """Generuje QSS WYŁĄCZNIE na akcenty (ramki, zaokrąglenia, stany).

    Świadomie NIE wpisuje kolorów bazowych (bg/bg2/bg3/fg/fg2/fg3) — te pochodzą
    z :class:`QPalette`. Dublowanie powodowałoby plamy przy zmianie motywu (QSS
    nadpisuje paletę). Wołane od zera przy każdym ``apply()`` — bez cache.
    """
    return f"""
QPushButton, QToolButton {{
    border: 1px solid {palette.border};
    border-radius: 6px;
    padding: 4px 12px;
}}
QPushButton:hover, QToolButton:hover {{
    background-color: {palette.hover};
}}
QPushButton:pressed, QToolButton:pressed {{
    background-color: {palette.pressed};
}}
QLineEdit, QPlainTextEdit, QTextEdit, QListWidget, QComboBox, QAbstractSpinBox {{
    border: 1px solid {palette.border};
    border-radius: 4px;
    padding: 2px 4px;
}}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus,
QComboBox:focus, QAbstractSpinBox:focus {{
    border: 1px solid {palette.focus_border};
}}
QGroupBox {{
    border: 1px solid {palette.border};
    border-radius: 6px;
    margin-top: 6px;
    padding-top: 6px;
}}
QTabWidget::pane {{
    border: 1px solid {palette.border};
    border-radius: 6px;
}}
QToolTip {{
    border: 1px solid {palette.border};
    padding: 4px;
}}
"""


def apply_theme(app: QApplication, palette: Palette) -> None:
    """Stosuje paletę do aplikacji wg kanonicznej sekwencji §4.

    Kolejność jest istotna: najpierw styl ``Fusion`` (inaczej natywny styl
    Windows zignoruje paletę), potem paleta, potem świeży QSS na akcenty, na
    końcu jawna paleta tooltipów i przemalowanie istniejących widgetów. Aktualizuje
    też paletę modułową (:func:`current_palette`).
    """
    app.setStyle("Fusion")
    qpalette = build_palette(palette)
    app.setPalette(qpalette)
    app.setStyleSheet(build_qss(palette))
    QToolTip.setPalette(qpalette)
    _repolish(app)
    # Jedyne wejście zapisu palety ikon — wspólne z konsumentami z własnym motywem.
    set_current_palette(palette)


def _repolish(app: QApplication) -> None:
    """Wymusza przemalowanie wszystkich widgetów po zmianie palety/QSS.

    Po ``unpolish``/``polish`` dodatkowo woła ``update()`` na każdym widgecie
    (i raz jeszcze na oknach top-level) — bez tego częściowo widoczne okna
    odświeżają się z opóźnieniem przy zmianie motywu systemu w tle (tryb auto).
    """
    style = app.style()
    for widget in app.allWidgets():
        style.unpolish(widget)
        style.polish(widget)
        widget.update()
    for window in app.topLevelWidgets():
        window.update()


class ThemeManager(QObject):
    """Zarządza motywem aplikacji (auto/jasny/ciemny) i jego trwałością.

    Emituje :attr:`theme_changed` z :class:`Palette` po każdej zmianie. Sygnał
    systemowy ``colorSchemeChanged`` jest podłączony wyłącznie w trybie auto
    (referencję połączenia trzymamy, by je odłączyć przy wymuszeniu motywu).

    Pasek tytułu okien dołącz przez :meth:`attach_titlebar` — przy każdym
    ``apply()`` DWM jest ustawiany BEZWARUNKOWO na motyw aplikacji dla wszystkich
    dołączonych okien (atrybut stanowy, GUI_STANDARD v2.5).

    Args:
        app: instancja :class:`QApplication`.
        config: słownik konfiguracji (np. :class:`chodzkos_gui_kit.config.Config`
            albo zwykły ``dict``) — czytany kluczem ``"theme"``.
    """

    theme_changed = Signal(object)

    def __init__(self, app: QApplication, config: MutableMapping[str, Any]) -> None:
        super().__init__()
        self._app = app
        self._config = config
        self._setting: ThemeSetting = self._initial_setting()
        self._palette: Palette = pal.DARK
        # Uchwyt połączenia colorSchemeChanged — None gdy nie subskrybujemy.
        self._auto_connection: object | None = None
        # Okna z dołączonym paskiem tytułu (DWM aktualizowany przy każdym apply).
        self._titlebar_syncs: list[titlebar.TitlebarSync] = []

    @property
    def setting(self) -> ThemeSetting:
        """Aktualne ustawienie trybu (auto/light/dark)."""
        return self._setting

    @property
    def palette(self) -> Palette:
        """Aktualnie zastosowana paleta (rozwiązana z ustawienia)."""
        return self._palette

    def _initial_setting(self) -> ThemeSetting:
        """Wczytuje ustawienie motywu z configu (domyślnie auto)."""
        value = self._config.get(THEME_KEY)
        return value if value in _THEME_SETTINGS else "auto"

    def resolved_name(self, setting: ThemeSetting | None = None) -> ThemeName:
        """Mapuje ustawienie na konkretny motyw (``auto`` → motyw systemu)."""
        chosen = setting if setting is not None else self._setting
        if chosen == "auto":
            return system_scheme()
        return "light" if chosen == "light" else "dark"

    def apply(self, setting: ThemeSetting) -> None:
        """Ustawia tryb, zapisuje go w configu i stosuje do aplikacji."""
        self._setting = setting
        self._config[THEME_KEY] = setting
        name = self.resolved_name(setting)
        self._palette = pal.DARK if name == "dark" else pal.LIGHT
        apply_theme(self._app, self._palette)
        self._sync_titlebars()
        self._update_auto_subscription()
        self.theme_changed.emit(self._palette)

    def attach_titlebar(self, window: QWidget) -> None:
        """Dołącza pasek tytułu okna do menedżera (DWM = motyw app, bezwarunkowo).

        Instaluje filtr zdarzeń, który re-aplikuje kolor belki przy pokazaniu i
        (de)aktywacji okna (``winId`` jest wiarygodny dopiero po ``showEvent``).
        Natychmiast synchronizuje belkę z bieżącym motywem.
        """
        sync = titlebar.TitlebarSync(window, lambda: mode_of(self._palette))
        self._titlebar_syncs.append(sync)
        sync.refresh()

    def _sync_titlebars(self) -> None:
        """Ustawia pasek tytułu wszystkich dołączonych okien na motyw aplikacji."""
        for sync in self._titlebar_syncs:
            sync.refresh()

    def _update_auto_subscription(self) -> None:
        """Podłącza ``colorSchemeChanged`` tylko w trybie auto, inaczej odłącza."""
        hints = self._app.styleHints()
        if self._setting == "auto" and self._auto_connection is None:
            self._auto_connection = hints.colorSchemeChanged.connect(self._on_system_scheme_changed)
        elif self._setting != "auto" and self._auto_connection is not None:
            hints.colorSchemeChanged.disconnect(self._auto_connection)
            self._auto_connection = None

    def _on_system_scheme_changed(self, _scheme: Qt.ColorScheme) -> None:
        """Gdy zmienia się motyw systemu, odśwież w trybie auto."""
        if self._setting == "auto":
            self.apply("auto")
