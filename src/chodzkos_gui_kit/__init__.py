"""chodzkos-gui-kit — implementacja GUI_STANDARD.md."""

from importlib.metadata import PackageNotFoundError, version

try:
    # Jedno źródło prawdy o wersji: pole `version` w pyproject.toml → metadane
    # zainstalowanego pakietu. Zero literału w kodzie (brak rozjazdu jak v0.5.0).
    __version__ = version("chodzkos-gui-kit")
except PackageNotFoundError:  # praca z drzewa źródeł bez instalacji pakietu
    __version__ = "0.0.0+unknown"
