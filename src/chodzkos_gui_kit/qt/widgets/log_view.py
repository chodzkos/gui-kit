"""Widget logu: ``QPlainTextEdit`` tylko do odczytu z kolorowaniem poziomów.

Łączy dwa wzorce konsumentów:

* **baza z EpubForge** — ``QPlainTextEdit`` read-only, limit bloków, mono Consolas,
  ``append_line(text, level)`` przez ``QTextCharFormat`` (bez HTML), 5 poziomów
  mapowanych na role palety;
* **re-render historii z pdf2md** — bufor wpisów + przemalowanie CAŁEJ historii
  przy zmianie motywu (``set_theme``), nie tylko nowych linii.

i18n: brak — widget pokazuje wyłącznie logi z aplikacji, nie ma własnych etykiet.

Poziomy są **rozszerzalne**: domyślne mapowanie poziom→rola palety można uzupełnić
parametrem ``level_colors`` (np. streaming transkrypcji: ``{"transcribing":
"accent2"}``), bez zmiany kitu. Wartości to nazwy ról palety (przeżywają zmianę
motywu w re-renderze) albo gotowe kolory — rola jest preferowana.
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QPlainTextEdit, QWidget

from chodzkos_gui_kit.palette import Palette
from chodzkos_gui_kit.qt.theme import current_palette

# Maksymalna liczba bloków (linii) — chroni przed rozrostem przy długich logach.
_MAX_BLOCKS = 5000

# Domyślne mapowanie poziom → nazwa roli palety (GUI_STANDARD §5).
_DEFAULT_LEVEL_ROLES: dict[str, str] = {
    "ok": "accent",
    "warn": "amber",
    "err": "red",
    "cmd": "fg3",
    "info": "fg2",
}
# Poziom nieznany → rola palety dla zwykłego tekstu.
_FALLBACK_ROLE = "fg"


class LogView(QPlainTextEdit):
    """Pole logu: kolorowane linie wg poziomu, z re-renderem przy zmianie motywu.

    Args:
        timestamps: gdy ``True``, każda linia dostaje prefiks ``[HH:MM:SS]``.
        level_colors: uzupełnia/nadpisuje domyślne mapowanie poziom→rola palety
            (wartość: nazwa roli palety, np. ``"accent2"``, albo gotowy kolor).
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        timestamps: bool = False,
        level_colors: dict[str, str] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumBlockCount(_MAX_BLOCKS)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        font = QFont("Consolas")
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)

        self._timestamps = timestamps
        self._level_roles = {**_DEFAULT_LEVEL_ROLES, **(level_colors or {})}
        self._palette: Palette = current_palette()
        # Źródło prawdy do przemalowania: (poziom, treść, timestamp|"").
        self._buffer: list[tuple[str, str, str]] = []

    # ── API ────────────────────────────────────────────────────────────────────

    def append_line(self, text: str, level: str = "info") -> None:
        """Dopisuje linię logu w kolorze odpowiadającym poziomowi."""
        ts = datetime.now().strftime("%H:%M:%S") if self._timestamps else ""
        self._buffer.append((level, text, ts))
        if len(self._buffer) > _MAX_BLOCKS:
            del self._buffer[: len(self._buffer) - _MAX_BLOCKS]
        self._render_line(level, text, ts)

    def log_info(self, text: str) -> None:
        """Komunikat informacyjny — poziom ``ok`` (akcent, NIE wyszarzony ``info``)."""
        self.append_line(text, "ok")

    def log_warning(self, text: str) -> None:
        """Ostrzeżenie — poziom ``warn`` (amber)."""
        self.append_line(text, "warn")

    def log_error(self, text: str) -> None:
        """Błąd — poziom ``err`` (red)."""
        self.append_line(text, "err")

    def set_theme(self, theme: Palette) -> None:
        """Zmienia motyw i przemalowuje CAŁĄ historię wg nowej palety."""
        self._palette = theme
        self._repaint_all()

    def clear(self) -> None:
        """Czyści widok i bufor wpisów."""
        self._buffer.clear()
        super().clear()

    # ── Render ───────────────────────────────────────────────────────────────--

    def _render_line(self, level: str, text: str, ts: str) -> None:
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(self._color_for(level)))
        line = f"[{ts}] {text}" if ts else text
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(line.rstrip("\n") + "\n", fmt)
        self.moveCursor(QTextCursor.MoveOperation.End)
        self.ensureCursorVisible()

    def _repaint_all(self) -> None:
        """Przemalowuje historię z bufora (po zmianie motywu) — czyści tylko widok."""
        super().clear()
        for level, text, ts in self._buffer:
            self._render_line(level, text, ts)

    def _color_for(self, level: str) -> str:
        """Kolor poziomu: rola palety (przeżywa zmianę motywu) lub gotowy kolor."""
        role_or_color = self._level_roles.get(level, _FALLBACK_ROLE)
        # Nazwa roli palety → jej bieżący kolor; inaczej traktuj jako gotowy kolor.
        resolved = getattr(self._palette, role_or_color, role_or_color)
        return str(resolved)
