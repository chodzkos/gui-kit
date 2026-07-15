# CLAUDE.md — zasady pracy w repo gui-kit

## Czym jest to repo

Biblioteka wspólnych komponentów GUI implementująca **GUI_STANDARD.md** (mieszka
w tym repo — przy każdej zmianie reguł aktualizuj OBA: kod i dokument, dopisując
wiersz w tabeli wersji standardu). Tag `vX.Y.Z` repo odpowiada stanowi standardu.

## Zasady żelazne (egzekwowane w review)

1. **Hexy kolorów istnieją WYŁĄCZNIE w `src/chodzkos_gui_kit/palette.py`.**
   QSS, słowniki tkinter, przykłady — wszystko generowane/odwołujące się do
   `Palette`. Grep po `#[0-9a-fA-F]{6}` poza palette.py i assets = błąd.
2. **QSS jest funkcją palety, nie stałą** — `build_qss(palette)` wołane przy
   każdym `apply()`. Zakaz cache'owania wygenerowanego stringa.
3. **Kanoniczna sekwencja `apply()`** (standard v2.3, nie zmieniać kolejności):
   `setPalette` → `setStyleSheet(build_qss(...))` → `QToolTip.setPalette(...)`
   → `unpolish/polish` + `update()` po `allWidgets()`.
4. **Rozjazd motywów obsługiwany symetrycznie** (titlebar i dialogi, oba
   kierunki); motyw systemu czytany w momencie użycia, nie cache'owany;
   `Unknown` → dark.
5. **`winutil/` nie importuje Qt ani tk** — to warstwa wspólna obu torów.
6. **Reguła trzech dla widgetów**: nowy widget tylko z dwoma realnymi
   konsumentami (wymień ich w opisie PR).
7. **Kod wchodzi przez ekstrakcję** ze sprawdzonej aplikacji, nie jest pisany
   "na zapas" w kicie.

## Workflow

- gałęzie: `feat/...`, `fix/...`, `refactor/...`; Conventional Commits
- jeden prompt = jedna gałąź = jeden PR; NIGDY auto-push
- przed commitem zawsze: `pytest`, `ruff --fix`, `mypy` (strict)
- środowisko: `uv sync --extra qt --extra dev`
- testy Qt lokalnie i na CI: `QT_QPA_PLATFORM=offscreen`
- testy wymagające realnego Windows/DWM: `@pytest.mark.windows`
  (domyślnie pomijane — addopts w pyproject)

## Wersjonowanie

- semver; wersja w `pyproject.toml` (`[project].version`), tag `vX.Y.Z` na commicie release
- **Konwencja pinowania (konsumenci): pinuj SHA commitu z komentarzem wersji**
  (`git+...@<SHA>  # vX.Y.Z`), **nigdy sam tag i nigdy `main`**. Tagi gitowe są mutowalne
  (lightweight = ruchoma nazwa) — SHA jest niezmienny; komentarz niesie czytelność. Decyzja:
  supply-chain hardening (audyt 07.2026), spójna z pdf2md/mediaforge.
- do v1.0: minor może łamać API (odnotuj w CHANGELOG pod "Breaking")
- od v1.0: zmiana sygnatur publicznych LUB reguł standardu (sekwencja apply,
  reguła rozjazdu) = MAJOR

## Pułapki środowiska (Windows/WSL — patrz też GUI_STANDARD §3-4)

- pliki kopiowane z WSL: usuwać strumienie `Zone.Identifier`
- pip w razie potrzeby systemowej: `--break-system-packages` (preferuj uv)
- testy palety muszą przechodzić bez zainstalowanego PySide6
  (palette.py i config.py = czysty Python + platformdirs)
