# chodzkos-gui-kit

Wspólne komponenty GUI dla aplikacji desktopowych (chodzkos): paleta marki, motywy dark/light z auto-detekcją, ciemny/jasny pasek tytułu Windows (DWM), dialogi plików z regułą rozjazdu motywów.

Implementacja zasad z **[GUI_STANDARD.md](GUI_STANDARD.md)** — dokument mieszka w tym repo i wersjonuje się razem z kodem (tag `vX.Y.Z` ↔ tabela wersji standardu).

## Instalacja (w aplikacji)

```bash
# tor Qt (PySide6):
uv add "chodzkos-gui-kit[qt] @ git+https://github.com/chodzkos/gui-kit@v0.1.1"

# tor tkinter:
uv add "chodzkos-gui-kit[tk] @ git+https://github.com/chodzkos/gui-kit@v0.2.0"
```

(używaj najnowszego taga — sprawdź [Releases](https://github.com/chodzkos/gui-kit/releases))

Pin do **taga**, nigdy do `main`. Podniesienie wersji = osobny commit `chore:` w aplikacji + przebieg testów.

## Architektura

```
palette.py        # WARSTWA 0: czyste dane — jedyne hexy w kicie (dark/light + stany)
config.py         # platformdirs + zapis atomowy + debounce
winutil/dwm.py    # WARSTWA 1: wspólny ctypes DWM (bez Qt, bez tk)
qt/               # WARSTWA 2a [extras: qt]
  theme.py        #   Fusion + QPalette + generator QSS; kanoniczna sekwencja apply()
  titlebar.py     #   reguła rozjazdu → winutil.dwm (HWND z winId)
  dialogs.py      #   natywny ⇔ zgodność motywów + skonfigurowany fallback
  widgets/        #   (od v0.3 — reguła trzech, patrz ROADMAP)
tk/               # WARSTWA 2b [extras: tk]
```

Zasady żelazne:
- **hexy tylko w `palette.py`** — QSS i słowniki tkinter są generowane,
- **QSS jest funkcją palety, nie stałą** — regenerowany przy każdym `apply()`,
- kanoniczna sekwencja `apply()`: `setPalette` → `setStyleSheet(świeży QSS)` → `QToolTip.setPalette` → `unpolish/polish` + `update()`,
- rozjazd motywów (app ≠ system) obsługiwany **symetrycznie** (titlebar i dialogi, oba kierunki).

Pełne uzasadnienia i pułapki: [GUI_STANDARD.md](GUI_STANDARD.md) §4–§5.

## Szybki start (Qt)

```python
from chodzkos_gui_kit.qt.theme import ThemeManager

app = QApplication([])
tm = ThemeManager(app)          # Fusion + paleta + QSS; tryb z configu (auto/dark/light)
tm.apply("auto")                # auto: styleHints().colorScheme(), Unknown → dark
window = MainWindow()
tm.attach_titlebar(window)      # DWM tylko przy rozjeździe, w obu kierunkach
```

## Status

Kod toru Qt pochodzi z ekstrakcji sprawdzonego kodu **EpubForge** (etapy F) — patrz `PROMPTS.md` P1. Tor tkinter: od v0.2. Widgety wspólne: od v0.3, tylko z dwoma realnymi konsumentami.

## Licencja

MIT. PySide6 (LGPL) jest zależnością opcjonalną, nie jest bundlowane.
