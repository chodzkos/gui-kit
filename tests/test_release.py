"""Testy warstwy 0 :mod:`chodzkos_gui_kit.release` — czysty Python, bez PySide6.

Sieć (``latest_github_release``) jest mockowana; logika porównania wersji
(``is_update_available``/``_version_key``) testowana bez sieci.
"""

from __future__ import annotations

from importlib.metadata import version

import chodzkos_gui_kit.release as rel


def test_installed_version_reads_metadata() -> None:
    """Dla realnie zainstalowanego pakietu zwraca wersję z metadanych, nie fallback."""
    assert rel.installed_version("chodzkos-gui-kit") == version("chodzkos-gui-kit")


def test_installed_version_fallback_for_unknown_dist() -> None:
    """Nieznana dystrybucja → jawny fallback konsumenta."""
    assert rel.installed_version("no-such-distribution-xyz", fallback="9.9.9") == "9.9.9"


def test_version_key_ignores_prefixes_and_suffixes() -> None:
    """Człon = wiodące cyfry; ``v`` i sufiksy pre-release są ucinane."""
    assert rel._version_key("1.3.0") == (1, 3, 0)
    assert rel._version_key("2.0") == (2, 0)
    assert rel._version_key("1.2.3-rc1") == (1, 2, 3)


def test_is_update_available_detects_newer() -> None:
    assert rel.is_update_available("1.2.0", "1.3.0") == (True, "1.3.0")
    # numeryczne, nie leksykalne (1.10 > 1.9):
    assert rel.is_update_available("1.9.0", "1.10.0") == (True, "1.10.0")


def test_is_update_available_same_or_older() -> None:
    assert rel.is_update_available("1.3.0", "1.3.0") == (False, "")
    assert rel.is_update_available("1.3.0", "1.2.9") == (False, "")


def test_is_update_available_offline_or_unknown() -> None:
    """Brak ``latest`` (offline) lub nieznana wersja zainstalowana → brak aktualizacji."""
    assert rel.is_update_available("1.3.0", None) == (False, "")
    assert rel.is_update_available("0.0.0", "1.3.0") == (False, "")
    assert rel.is_update_available("", "1.3.0") == (False, "")


def test_latest_github_release_parses_tag(monkeypatch) -> None:
    """Poprawna odpowiedź API → tag bez wiodącego ``v``."""

    class _Resp:
        def __enter__(self) -> _Resp:
            return self

        def __exit__(self, *exc: object) -> None:
            return None

        def read(self) -> bytes:
            return b'{"tag_name": "v2.1.0"}'

    monkeypatch.setattr(rel.urllib.request, "urlopen", lambda *a, **k: _Resp())
    assert rel.latest_github_release("chodzkos", "gui-kit") == "2.1.0"


def test_latest_github_release_network_error_returns_none(monkeypatch) -> None:
    """Wyjątek sieci/parsowania → ``None`` (nie wyjątek)."""

    def _boom(*a: object, **k: object) -> None:
        raise OSError("no network")

    monkeypatch.setattr(rel.urllib.request, "urlopen", _boom)
    assert rel.latest_github_release("chodzkos", "gui-kit") is None


def test_check_github_update_composes(monkeypatch) -> None:
    """Skrót łączy wersję zainstalowaną z najnowszym wydaniem."""
    monkeypatch.setattr(rel, "installed_version", lambda *a, **k: "1.0.0")
    monkeypatch.setattr(rel, "latest_github_release", lambda *a, **k: "1.4.0")
    assert rel.check_github_update("icoforge", "chodzkos", "icoforge") == (True, "1.4.0")
