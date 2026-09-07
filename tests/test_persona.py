from callsign.persona import build_messages, load_persona


def test_load_persona(tmp_path):
    p = tmp_path / "persona.md"
    p.write_text("Jesteś asystentem.\n", encoding="utf-8")
    assert load_persona(str(p)) == "Jesteś asystentem."


def test_build_messages_shape():
    msgs = build_messages("SYS", [("cześć", "no siema")], "co robisz?")
    assert msgs[0] == {"role": "system", "content": "SYS"}
    assert msgs[1] == {"role": "user", "content": "cześć"}
    assert msgs[2] == {"role": "assistant", "content": "no siema"}
    assert msgs[-1] == {"role": "user", "content": "co robisz?"}
