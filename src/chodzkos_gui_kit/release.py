"""Introspekcja wersji i sprawdzanie aktualizacji przez GitHub Releases.

Warstwa 0 kitu (czysty Python, **zero Qt/tk**) wg GUI_STANDARD §8 („O programie"
z wersją i sprawdzaniem aktualizacji). Ekstrakcja sprawdzonego `version_check`
z IcoForge; odsprzężona od aplikacji przez parametry (`dist_name`/`owner`/`repo`,
`fallback`).

Jedno źródło prawdy o wersji: :func:`installed_version` czyta metadane
zainstalowanego pakietu (jak :data:`chodzkos_gui_kit.__version__`), z jawnym
`fallback` po stronie konsumenta (np. wygenerowany `app/_version.py` w buildzie
frozen bez `.dist-info`).

Porównanie wersji jest **bez zależności** (`packaging` NIE jest wymagane): tagi
wydań (`1.3.0`, `v2.0`) porównujemy numerycznie krotką z :func:`_version_key`.
Człony nie-numeryczne (pre-release `-rc1`) są ucinane — dla porównań „czy jest
nowszy stabilny release" to wystarcza, a kit nie ciągnie nowej zależności.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 5.0
_DEFAULT_USER_AGENT = "chodzkos-gui-kit"


def installed_version(dist_name: str, *, fallback: str = "0.0.0") -> str:
    """Zwraca wersję zainstalowanego pakietu ``dist_name``.

    Kolejność: ``importlib.metadata.version`` (działa w dev i w bundlu frozen,
    gdy spec dokłada ``copy_metadata(dist_name)``) → ``fallback`` gdy metadanych
    brak (starszy bundle bez ``.dist-info`` / praca z drzewa źródeł bez instalacji).

    Args:
        dist_name: nazwa dystrybucji (np. ``"icoforge"``).
        fallback: wartość zwracana, gdy metadanych nie ma (np. ``app._version.__version__``).

    Returns:
        Ciąg wersji (np. ``"1.3.0"``) albo ``fallback``.
    """
    try:
        return _pkg_version(dist_name)
    except PackageNotFoundError:
        return fallback
    except Exception as exc:  # metadane nieczytelne — nie wywracamy „O programie"
        logger.debug("installed_version(%s): %s", dist_name, exc)
        return fallback


def github_releases_url(owner: str, repo: str) -> str:
    """Adres strony wydań repozytorium (link „Dostępna aktualizacja")."""
    return f"https://github.com/{owner}/{repo}/releases"


def latest_github_release(
    owner: str,
    repo: str,
    *,
    timeout: float = _DEFAULT_TIMEOUT,
    user_agent: str = _DEFAULT_USER_AGENT,
) -> str | None:
    """Pobiera tag najnowszego wydania z GitHub Releases API.

    Args:
        owner: właściciel repozytorium (użytkownik/organizacja).
        repo: nazwa repozytorium.
        timeout: limit czasu żądania (sekundy).
        user_agent: nagłówek ``User-Agent`` (GitHub API wymaga niepustego).

    Returns:
        Wersja bez wiodącego ``v`` (np. ``"1.3.0"``), albo ``None`` gdy sieć jest
        niedostępna lub odpowiedź jest niepoprawna.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": user_agent, "Accept": "application/vnd.github+json"},
        )
        # Stały adres https://api.github.com — brak wstrzyknięcia schematu/hosta.
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read())
    except Exception as exc:  # sieć/timeout/parsowanie — brak informacji, nie błąd krytyczny
        logger.debug("latest_github_release(%s/%s): %s", owner, repo, exc)
        return None
    if not isinstance(payload, dict):
        return None
    tag = str(payload.get("tag_name", ""))
    return tag.lstrip("v") or None


def _version_key(value: str) -> tuple[int, ...]:
    """Numeryczny klucz porównania wersji (człon = wiodące cyfry, reszta ucięta)."""
    parts: list[int] = []
    for chunk in value.split("."):
        digits = ""
        for ch in chunk:
            if ch.isdigit():
                digits += ch
            else:
                break
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def _is_newer(latest: str, installed: str) -> bool:
    """Czy ``latest`` jest wersją nowszą niż ``installed`` (porównanie numeryczne)."""
    a = _version_key(latest)
    b = _version_key(installed)
    length = max(len(a), len(b))
    a += (0,) * (length - len(a))
    b += (0,) * (length - len(b))
    return a > b


def is_update_available(installed: str, latest: str | None) -> tuple[bool, str]:
    """Porównuje wersję zainstalowaną z najnowszą (funkcja czysta, bez sieci).

    Args:
        installed: wersja zainstalowana (z :func:`installed_version`).
        latest: najnowsza wersja (z :func:`latest_github_release`) albo ``None``.

    Returns:
        ``(True, "1.3.0")`` gdy dostępna nowsza; inaczej ``(False, "")``
        (także offline ``latest is None`` lub gdy ``installed`` jest pusty/nieznany).
    """
    if not latest or not installed or not any(_version_key(installed)):
        return False, ""
    return (True, latest) if _is_newer(latest, installed) else (False, "")


def check_github_update(
    dist_name: str,
    owner: str,
    repo: str,
    *,
    timeout: float = _DEFAULT_TIMEOUT,
    fallback: str = "0.0.0",
) -> tuple[bool, str]:
    """Wygodny skrót: wersja zainstalowana vs najnowsze wydanie GitHub.

    Woła sieć (:func:`latest_github_release`) — uruchamiaj w wątku/tle
    (GUI nie może blokować). Zwraca kontrakt :func:`is_update_available`.
    """
    installed = installed_version(dist_name, fallback=fallback)
    latest = latest_github_release(owner, repo, timeout=timeout)
    return is_update_available(installed, latest)
