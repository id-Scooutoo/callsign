"""Grep a local clone of the codebase so the bot can point to responsible
modules/files. Read-only; returns a short file list as LLM context."""
import subprocess

from .wake import wake_forms

_STOP = {
    "gdzie", "jest", "ktory", "który", "ktora", "która", "modul", "moduł",
    "moduly", "moduły", "kod", "kodzie", "plik", "pliku", "pliki", "jak",
    "dziala", "działa", "co", "robi", "za", "odpowiedzialny", "odpowiada",
    "the", "is", "file", "module", "pokaz", "pokaż", "wskaz",
    "który", "obsluguje", "obsługuje", "and", "for",
}


def _terms(query: str, wake_word: str = "") -> list[str]:
    # The bot is usually addressed by name in the same sentence, and its own
    # name is never a useful grep term — drop every inflected form of it.
    stop = _STOP | set(wake_forms(wake_word))
    words = [w.strip(".,?!:;\"'()[]").lower() for w in query.split()]
    return [w for w in words if len(w) >= 3 and w not in stop][:5]


def search(query: str, repo_path: str, max_files: int = 10, wake_word: str = "") -> str:
    if not repo_path:
        return ""
    terms = _terms(query, wake_word)
    if not terms:
        return ""
    pattern = "|".join(terms)
    try:
        out = subprocess.run(
            [
                "grep", "-rilE",
                "--include=*.py", "--include=*.ts", "--include=*.tsx",
                "--include=*.js", "--include=*.md",
                "--exclude-dir=node_modules", "--exclude-dir=.git",
                "--exclude-dir=dist", "--exclude-dir=__pycache__",
                "--exclude-dir=migrations", "--exclude-dir=.venv",
                pattern, repo_path,
            ],
            capture_output=True, text=True, timeout=20,
        ).stdout
    except Exception:  # noqa: BLE001
        return ""
    base = repo_path.rstrip("/") + "/"
    files = [f.replace(base, "") for f in out.splitlines() if f][:max_files]
    if not files:
        return ""
    listing = "\n".join("- " + f for f in files)
    return f"Pliki w kodzie pasujące do pytania (wskaż odpowiedni moduł):\n{listing}"
