"""Panel „O programie" (logo, wersja, linki) świadomy motywu (GUI_STANDARD §7, §8).

Ekstrakcja sprawdzonego okna „O programie" z IcoForge; odsprzężona od aplikacji:
treść to parametry, i18n przez :class:`AboutTexts` (frozen dataclass, domyślne po
angielsku), a sprawdzanie aktualizacji jest wstrzykiwanym ``check_update``
(kit nie zna nazwy pakietu ani repo — te zna konsument, np. przez
:func:`chodzkos_gui_kit.release.check_github_update`).

Sprawdzanie aktualizacji jest **asynchroniczne** (osobny wątek — GUI nie może
blokować na sieci). Panel sam zarządza cyklem życia wątku: startuje przy
pierwszym pokazaniu, a zatrzymuje (``quit``/``wait``) przy zamknięciu okna
(``Close`` okna-rodzica) — dzięki temu osadzenie panelu w zwykłym ``QDialog`` nie
wymaga po stronie konsumenta ręcznego sprzątania wątku.

Motyw: etykiety i linki dziedziczą kolory z palety aplikacji (``QPalette``), więc
podążają za motywem bez re-renderu. Logo może mieć warianty jasny/ciemny —
podaj ``logo`` jako ``Callable[[], QPixmap | None]``, a panel przeładuje je przy
``PaletteChange`` (statyczny ``QPixmap`` zostaje bez zmian).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from PySide6.QtCore import QEvent, QObject, Qt, QThread, Signal
from PySide6.QtGui import QCloseEvent, QPixmap, QShowEvent
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


@dataclass(frozen=True)
class AboutTexts:
    """Teksty UI :class:`AboutPanel` (domyślnie po angielsku — aplikacja tłumaczy).

    Pola z ``{...}`` to szablony ``str.format``: ``version_label`` dostaje
    ``version``, ``update_available`` dostaje ``version``, ``license_label``
    dostaje ``name``.
    """

    version_label: str = "Version {version}"
    checking_update: str = "Checking for updates…"
    up_to_date: str = "You have the latest version."
    update_available: str = "Update available: {version}"
    license_label: str = "License: {name}"


class _UpdateWorker(QThread):
    """Wątek jednorazowego sprawdzenia aktualizacji (woła ``check`` i emituje wynik)."""

    result = Signal(bool, str)

    def __init__(
        self, check: Callable[[], tuple[bool, str]], parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._check = check

    def run(self) -> None:
        try:
            available, version = self._check()
        except Exception:  # sieć/parsowanie po stronie konsumenta — brak aktualizacji
            available, version = False, ""
        self.result.emit(available, version)


class AboutPanel(QWidget):
    """Panel „O programie": logo, nazwa, wersja, status aktualizacji, opis, linki, licencja.

    Args:
        app_name: nazwa aplikacji (pogrubiona, wyśrodkowana).
        version: wersja aplikacji (z :func:`chodzkos_gui_kit.release.installed_version`).
        description: krótki opis (zawijany); pusty → pomijany.
        links: sekwencja ``(etykieta, url)`` renderowanych jako klikalne odnośniki.
        license_name: nazwa licencji (np. ``"MIT"``); ``None`` → wiersz pomijany.
        extra_note: dodatkowy wiersz (np. o licencjach firm trzecich); zawijany.
        logo: ``QPixmap`` albo ``Callable[[], QPixmap | None]`` (wariant motywu,
            przeładowywany przy ``PaletteChange``); ``None`` → bez logo.
        logo_width: docelowa szerokość logo w px (skalowane z zachowaniem proporcji).
        check_update: funkcja ``() -> (dostępna, wersja)`` wołana w tle; ``None`` →
            wiersz statusu aktualizacji pomijany.
        releases_url: adres strony wydań (link, gdy dostępna aktualizacja).
        texts: etykiety UI (domyślnie ang.).
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        app_name: str,
        version: str,
        description: str = "",
        links: Sequence[tuple[str, str]] = (),
        license_name: str | None = None,
        extra_note: str = "",
        logo: QPixmap | Callable[[], QPixmap | None] | None = None,
        logo_width: int = 200,
        check_update: Callable[[], tuple[bool, str]] | None = None,
        releases_url: str | None = None,
        texts: AboutTexts | None = None,
    ) -> None:
        super().__init__(parent)
        self._texts = texts or AboutTexts()
        self._logo_source = logo
        self._logo_width = logo_width
        self._check_update = check_update
        self._releases_url = releases_url
        self._worker: _UpdateWorker | None = None
        self._started = False
        self._filtered_window: QWidget | None = None

        self._build_ui(app_name, version, description, links, license_name, extra_note)

    def _build_ui(
        self,
        app_name: str,
        version: str,
        description: str,
        links: Sequence[tuple[str, str]],
        license_name: str | None,
        extra_note: str,
    ) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(20, 20, 20, 20)

        self._logo_label = QLabel()
        self._logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._logo_label)
        self._refresh_logo()

        name_label = QLabel(f"<b style='font-size:16px'>{app_name}</b>")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name_label)

        version_label = QLabel(self._texts.version_label.format(version=version))
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)

        if self._check_update is not None:
            self._update_label = QLabel(self._texts.checking_update)
            self._update_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._update_label.setOpenExternalLinks(True)
            layout.addWidget(self._update_label)

        if description:
            desc_label = QLabel(description)
            desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            desc_label.setWordWrap(True)
            layout.addWidget(desc_label)

        for text, url in links:
            link_label = QLabel(f'<a href="{url}">{text}</a>')
            link_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            link_label.setOpenExternalLinks(True)
            layout.addWidget(link_label)

        if license_name:
            license_label = QLabel(self._texts.license_label.format(name=license_name))
            license_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(license_label)

        if extra_note:
            note_label = QLabel(extra_note)
            note_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            note_label.setWordWrap(True)
            layout.addWidget(note_label)

    # ── Logo (wariant motywu) ──────────────────────────────────────────────────

    def _refresh_logo(self) -> None:
        """Ustawia (lub czyści) logo, wołając ``logo`` gdy jest funkcją motywu."""
        source = self._logo_source
        pixmap = source() if callable(source) else source
        if pixmap is not None and not pixmap.isNull():
            mode = Qt.TransformationMode.SmoothTransformation
            self._logo_label.setPixmap(pixmap.scaledToWidth(self._logo_width, mode))
            self._logo_label.show()
        else:
            self._logo_label.clear()
            self._logo_label.hide()

    # ── Cykl życia sprawdzania aktualizacji ────────────────────────────────────

    def start_update_check(self) -> None:
        """Uruchamia asynchroniczne sprawdzenie aktualizacji (idempotentne)."""
        if self._check_update is None or self._started:
            return
        self._started = True
        self._worker = _UpdateWorker(self._check_update, self)
        self._worker.result.connect(self._on_update_result)
        self._worker.start()

    def stop_update_check(self) -> None:
        """Zatrzymuje wątek sprawdzania (``quit``/``wait``) — bezpieczne wielokrotnie."""
        worker = self._worker
        if worker is not None:
            worker.quit()
            worker.wait()
            self._worker = None

    def _on_update_result(self, available: bool, version: str) -> None:
        """Aktualizuje wiersz statusu po zakończeniu sprawdzenia."""
        if available and self._releases_url:
            text = self._texts.update_available.format(version=version)
            self._update_label.setText(f'<a href="{self._releases_url}">{text}</a>')
        elif available:
            self._update_label.setText(self._texts.update_available.format(version=version))
        else:
            self._update_label.setText(self._texts.up_to_date)

    # ── Zdarzenia Qt ───────────────────────────────────────────────────────────

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802 — Qt API
        """Startuje sprawdzenie przy pierwszym pokazaniu i pilnuje zamknięcia okna."""
        super().showEvent(event)
        self.start_update_check()
        window = self.window()
        # Osadzony w dialogu: „Close" trafia do okna-rodzica, nie do panelu — filtr
        # na oknie łapie zamknięcie i sprząta wątek bez udziału konsumenta.
        if window is not self and window is not self._filtered_window:
            window.installEventFilter(self)
            self._filtered_window = window

    def changeEvent(self, event: QEvent) -> None:  # noqa: N802 — Qt API
        """Przeładowuje logo przy zmianie motywu (gdy podano wariant funkcyjny)."""
        if event.type() == QEvent.Type.PaletteChange and callable(self._logo_source):
            self._refresh_logo()
        super().changeEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 — Qt API
        """Sprząta wątek, gdy panel jest oknem najwyższego poziomu."""
        self.stop_update_check()
        super().closeEvent(event)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802 — Qt API
        """Sprząta wątek przy zamknięciu okna-rodzica (panel osadzony w dialogu)."""
        if obj is self._filtered_window and event.type() == QEvent.Type.Close:
            self.stop_update_check()
        return False
