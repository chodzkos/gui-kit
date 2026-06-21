# Changelog

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
