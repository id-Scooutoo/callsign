"""Lightweight web search (DuckDuckGo, no API key) to feed the bot fresh facts
(weather, news, prices, results) it can't know on its own."""
import re

_TRIGGERS = re.compile(
    r"\b(sprawd[źz]|wyszukaj|poszukaj|znajd[źz]|wygoogl|google|"
    r"w internecie|w sieci|w google|"
    r"pogod|weather|temperatur|deszcz|śnieg|opad|wiatr|"
    r"news|wiadomo[śs]c|aktualn|najnowsz|ostatni|dzisiaj|dzi[sś]|teraz|wczoraj|"
    r"kurs|cena|cen[ay]|ile kosztuj|ile ma|notowani|"
    r"wynik|mecz|kto wygra|kto to|co to za|kiedy (jest|był|będzie|wychodzi)|"
    r"co si[eę] dzieje|co nowego|co s[lł]ycha[cć] w|20(2[4-9]|3\d))\b",
    re.IGNORECASE,
)

# The model admitting it lacks live/current info -> trigger a fallback search.
_UNSURE = re.compile(
    r"nie ma[mj].{0,20}dost[eę]p|nie mog[eę].{0,15}sprawdzi|"
    r"nie wiem na bie[żz]|czasie rzeczywistym|real.?time|"
    r"nie mam.{0,20}(aktualn|bie[żz]|informacj|danych)|"
    r"nie posiadam.{0,20}(aktualn|informacj|dost)|"
    r"nie jestem w stanie sprawdzi|nie mam mo[żz]liwo[śs]ci sprawdzi|"
    r"moja wiedza (jest )?(ograniczona|si[eę] ko[ńn]czy)|data.{0,10}(cutoff|granicz)",
    re.IGNORECASE,
)


def needed(text: str) -> bool:
    """True if the query likely needs fresh, real-world info."""
    return bool(_TRIGGERS.search(text))


def looks_unsure(reply: str) -> bool:
    """True if the model said it can't access current/live info."""
    return bool(_UNSURE.search(reply))


def search_context(query: str, max_results: int = 5) -> str:
    """Top DuckDuckGo results as compact text. Empty string on any failure."""
    try:
        from ddgs import DDGS

        with DDGS() as ddg:
            hits = list(ddg.text(query, max_results=max_results))
    except Exception:  # noqa: BLE001 - never let search break a reply
        return ""
    lines = []
    for h in hits:
        title = (h.get("title") or "").strip()
        body = (h.get("body") or "").strip()
        if title or body:
            lines.append(f"- {title}: {body}")
    return "\n".join(lines)
