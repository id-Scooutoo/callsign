import pytest

from callsign.wake import contains_wake, wake_forms


def test_ek_name_matches_base_and_vocative():
    assert contains_wake("hej marek co tam", "marek")
    assert contains_wake("Marku, słyszysz?", "marek")
    assert contains_wake("powiedz to markowi", "marek")


def test_consonant_name_matches_inflections():
    assert contains_wake("olaf, jaki mamy status", "olaf")
    assert contains_wake("Olafie, słyszysz?", "olaf")
    assert contains_wake("zapytaj olafa o to", "olaf")


def test_a_name_matches_inflections():
    assert contains_wake("kuba co robisz", "kuba")
    assert contains_wake("Kubo, halo?", "kuba")
    assert contains_wake("daj to kubie", "kuba")


def test_non_polish_name_matches_exactly():
    assert contains_wake("hey jarvis, status", "jarvis")
    assert contains_wake("wake up r2d2", "r2d2")


@pytest.mark.parametrize(
    "text, wake",
    [
        # The stem of "marek" prefixes plenty of unrelated words.
        ("marketing rośnie w tym kwartale", "marek"),
        # A handle with digits must not match a bare prefix.
        ("r2d 2 jest tutaj", "r2d2"),
        ("nic tu nie ma", "marek"),
    ],
)
def test_ignores_unrelated_words(text, wake):
    assert not contains_wake(text, wake)


def test_blank_wake_word_never_matches():
    assert not contains_wake("cokolwiek tu jest", "")
    assert wake_forms("") == ()


def test_forms_are_deduplicated():
    forms = wake_forms("olaf")
    assert len(forms) == len(set(forms))
    assert "olaf" in forms
