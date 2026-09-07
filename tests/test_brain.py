from callsign import brain as brain_mod
from callsign.brain import Brain, strip_think


def test_strip_think():
    assert strip_think("<think>hmm</think>No siema.") == "No siema."
    assert strip_think("Bez myślenia.") == "Bez myślenia."


def test_reply_posts_and_records_history(monkeypatch):
    captured = {}

    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"message": {"content": "<think>x</think>No elo."}}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["messages"] = json["messages"]
        return FakeResp()

    monkeypatch.setattr(brain_mod.requests, "post", fake_post)

    b = Brain(url="http://h:11434", model="qwen3:8b", persona="SYS")
    out = b.reply("cześć")
    assert out == "No elo."
    assert captured["url"] == "http://h:11434/api/chat"
    assert captured["messages"][0] == {"role": "system", "content": "SYS"}
    assert b.history == [("cześć", "No elo.")]
