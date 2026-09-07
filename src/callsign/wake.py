"""Decide whether a transcript addresses the bot by its configured name.

Polish inflects names, so someone saying "Marku, slyszysz?" is addressing a bot
called "marek". Rather than pull in a morphology library for one job, we
enumerate the handful of case endings a personal name actually takes, picked by
the shape of the name. Enumerating exact forms -- instead of matching a stem
plus a wildcard -- is what keeps "marketing" from waking a bot called "marek".

Names that are not Polish personal names (an English word, a call sign, a handle
with digits) fall back to an exact whole-word match.
"""
import re
from functools import lru_cache

# Marek -> Marka, Markowi, Markiem, Marku (the stem drops its "e").
_EK_ENDINGS = ("a", "owi", "iem", "u")
# Kuba -> Kuby, Kubie, Kubo, Kube.
_A_ENDINGS = ("a", "y", "ie", "o", "ę", "ą")
# Olaf -> Olafa, Olafowi, Olafem, Olafie, Olafu.
_CONSONANT_ENDINGS = ("a", "owi", "em", "ie", "u")

_LETTERS_ONLY = re.compile(r"^[^\W\d_]+$", re.UNICODE)


@lru_cache(maxsize=32)
def wake_forms(wake_word: str) -> tuple[str, ...]:
    """Every spelling of ``wake_word`` that counts as addressing the bot."""
    word = wake_word.strip().lower()
    if not word:
        return ()
    if not _LETTERS_ONLY.match(word):
        return (word,)

    if word.endswith("ek") and len(word) > 3:
        stem = word[:-2] + "k"
        forms = [word, *(stem + e for e in _EK_ENDINGS)]
    elif word.endswith("a") and len(word) > 2:
        stem = word[:-1]
        forms = [stem + e for e in _A_ENDINGS]
    else:
        forms = [word, *(word + e for e in _CONSONANT_ENDINGS)]

    # dict.fromkeys drops duplicates while keeping first-seen order.
    return tuple(dict.fromkeys(forms))


@lru_cache(maxsize=32)
def _pattern(wake_word: str) -> re.Pattern | None:
    forms = wake_forms(wake_word)
    if not forms:
        return None
    # Longest alternative first, so a longer form wins over one that prefixes it.
    alternatives = "|".join(re.escape(f) for f in sorted(forms, key=len, reverse=True))
    return re.compile(rf"\b(?:{alternatives})\b")


def contains_wake(text: str, wake_word: str) -> bool:
    """True if the transcript addresses the bot by name, in any case form."""
    pattern = _pattern(wake_word)
    return bool(pattern and pattern.search(text.lower()))
