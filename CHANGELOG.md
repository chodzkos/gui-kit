# Changelog

## [0.3.4]
### Fixed
- **`_repolish` repaintuje item-views** (`qt/theme.py`): po zmianie motywu wymusza `setPalette(app.palette())` + `viewport().update()` na `QAbstractItemView` (`QTableWidget`/`QTreeView`…). Naprawia stary ciemny `Base` po `dark→light` (Qt nie czyści per-widget resolve mask). **Celowane na item-views** (nie globalnie); flaga `apply_theme(..., repaint_item_views=True)` pozwala wyłączyć. GUI_STANDARD §4 v2.10.

### Added
- **`save_file(initial_name=…)`** (`qt/dialogs.py`): prefill nazwy zapisywanego pliku, **symetrycznie** w obu gałęziach — natywna przekazuje pełną ścieżkę w `dir` `getSaveFileName`, fallback woła `selectFile`. `initial_name=None` → zachowanie jak dotąd.

## [0.3.3]
### Fixed
- **Repaint ramki DWM** (`winutil/dwm.py`): po zmianie koloru paska dokładamy synchroniczne `RedrawWindow(RDW_FRAME | RDW_INVALIDATE | RDW_UPDATENOW | RDW_NOCHILDREN)` (z `argtypes`, uchwyt pointer-sized). Niweluje artefakt **Windows 10** — jasne tło pod tekstem tytułu po włączeniu `DWMWA_USE_IMMERSIVE_DARK_MODE`. Domyka parzystość z GUI_STANDARD §4 (który już przewidywał `WM_NCACTIVATE` + `RedrawWindow(RDW_FRAME)`).

## [0.3.2]
### Fixed
- **DWM HWND marshaling** (`winutil/dwm.py`): wywołania `DwmSetWindowAttribute`/`SetWindowPos`/`SendMessageW` dostały jawne `argtypes` z uchwytem jako `wintypes.HWND` (pointer-sized) + `restype`. Naprawia **truncację 64-bit HWND na Win64** — bez `argtypes` ctypes marshalował goły Python int jako 32-bit `c_int`, przez co DWM/pasek tytułu działał na części okien, na innych nie. Dotyczy wszystkich konsumentów (Qt i tk). GUI_STANDARD §4 v2.9.

## [0.3.1]
### Added
- **`qt.theme.set_current_palette(palette)`** — publiczne ustawianie palety odczytywanej przez `IconProvider`, dla konsumentów z WŁASNYM motywem (np. qdarktheme): pozwala przebarwić ikony **bez przemalowania aplikacji** (żadnego `setPalette`/`setStyleSheet`). `apply_theme()` przechodzi teraz przez ten sam setter, więc istnieje dokładnie **jedno wejście zapisu** `_current` (brak rozjazdu koloru ikon z motywem UI). GUI_STANDARD §5 v2.8 sankcjonuje to jako wyjątek w ramach zasady „kolory tylko z palety".

## [0.3.0]
### Added
- **`qt/icons.py` — `IconProvider` (przebarwialne SVG Lucide)** — ekstrakcja z IcoForge (pierwszy komponent v0.3, GUI_STANDARD §5/§7):
  - `get_icon(name, color=None, size=20) -> QIcon`: podmiana `currentColor` na kolor z palety, render z obsługą HiDPI (`devicePixelRatio`), cache `(name, hex, size)`, `clear_cache()` do wołania na zmianę motywu.
  - kolory WYŁĄCZNIE z `chodzkos_gui_kit.palette` (token → pole bieżącej palety przez `current_palette()`); domyślnie `fg`, semantyczne `red`/`amber`/`accent`, token `accent_text` (dark→accent, light→accent2) dla ikon w roli tekstu (reguła kontrastu §5). Zero hexów poza `palette.py`.
  - `ICON_MAP` (akcja → plik SVG) jako jedyne miejsce zmiany zestawu; `assets/icons/` (21 ikon Lucide) + `LICENSE-icons` (ISC) pakowane do wheela.
  - bez zależności cyklicznej: `icons` zna paletę, nie `ThemeManager` (`theme` nie importuje `icons`). Integracja po stronie aplikacji: `theme_changed.connect(clear_cache)` + ponowny `setIcon`.

## [0.2.0]
### Added
- **Tor tkinter** (`tk/`, extra `[tk]`) — ekstrakcja kodu tkinter EpubForge sprzed migracji na Qt (commit `f62266b^`):
  - `tk/theme.py` — `apply_theme(root, palette)`: `ttk.Style` (clam) + rekurencyjne kolorowanie klasycznych widgetów (Listbox/Text/Canvas…); `ThemeManager.apply("auto"|"light"|"dark")` równoległy do toru Qt; auto przez `darkdetect` (None/nieznane → dark); opcjonalny `darkdetect.listener` jako wątek daemon z marshalingiem na główny wątek Tk (`root.after`); persist trybu przez wstrzyknięty `Config`. Czyste, testowalne bez wyświetlacza funkcje `palette_colors`/`widget_options` (mapowanie roli → pole `Palette`).
  - `tk/titlebar.py` — `set_titlebar_dark`/`sync_titlebar`: HWND z `GetParent(winfo_id())`, dalej WYŁĄCZNIE wspólny `winutil.dwm.set_titlebar` (ten sam DWM co tor Qt; zero duplikacji ctypes DWM); ustawiany bezwarunkowo wg motywu app (v2.5).
  - kolory wyłącznie z `palette.py` (zero hexów w `tk/*`); `tk` nie importuje PySide6.
  - testy: mapowanie palety/`widget_options`, `system_scheme` (mock `darkdetect`), titlebar; testy żywego roota Tk pod markerem `tk`, DWM pod `windows`. CI instaluje `--extra tk`.

### Changed
- spójność palety: dawne tkinterowe `LIGHT.bg2 = #f5f5f5` zastąpione wartością z `palette.py` (`#f5f5f7`, §5) — bez przenoszenia starych hexów.

## [0.1.1]
### Fixed
- dołączono marker `py.typed` (PEP 561) — konsumenci (np. EpubForge) dostają typy kitu w `mypy --strict` bez `ignore_missing_imports`

## [0.1.0]
### Added
- szkielet repo: palette.py (paleta + stany z GUI_STANDARD §5), pyproject z extras, CI, dokumentacja (README, ROADMAP, PROMPTS, CLAUDE.md), GUI_STANDARD.md v2.7
- ekstrakcja rdzenia Qt z EpubForge (PROMPTS P1):
  - `winutil/dwm.py` — `set_titlebar(hwnd, dark)`: czysty ctypes (DwmSetWindowAttribute 20/19, WM_NCACTIVATE 0→1, SetWindowPos FRAMECHANGED), zero Qt/tk, no-op poza Windows
  - `config.py` — generyczny `Config(app_name)` (platformdirs, zapis atomowy tmp+replace, `get`/`set`/`mark_dirty`/`flush`, hak `on_dirty` pod debounce, wariant portable)
  - `qt/theme.py` — `ThemeManager`: Fusion przed setPalette, paleta i `build_qss` z `palette.py` (zero lokalnych hexów), kanoniczna sekwencja `apply()` (v2.3), auto przez `colorScheme()` (Unknown→dark), `attach_titlebar`
  - `qt/titlebar.py` — `sync_titlebar`/`TitlebarSync`: DWM = motyw app BEZWARUNKOWO (v2.5), re-aplikacja przy Show/ActivationChange
  - `qt/dialogs.py` — natywny ⇔ zgodność motywów (symetrycznie, v2.2); fallback QFileDialog (sidebar, Detail, rozmiar z config, fix przycisków toolbara v2.6)
  - testy `pytest-qt` (offscreen) dla theme/titlebar/dialogs + testy `config` bez PySide6; testy DWM przygotowane pod marker `windows`
