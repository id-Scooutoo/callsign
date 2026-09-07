from callsign.dialog_fsm import DialogFSM, State


def test_starts_sleeping():
    assert DialogFSM(timeout=20).state == State.SLEEPING


def test_wake_moves_to_listening():
    fsm = DialogFSM(timeout=20)
    fsm.on_wake(now=100.0)
    assert fsm.state == State.LISTENING


def test_listening_times_out_to_sleeping():
    fsm = DialogFSM(timeout=20)
    fsm.on_wake(now=100.0)
    assert fsm.tick(now=119.0) == State.LISTENING
    assert fsm.tick(now=120.0) == State.SLEEPING


def test_utterance_resets_the_window():
    fsm = DialogFSM(timeout=20)
    fsm.on_wake(now=100.0)
    fsm.on_utterance(now=115.0)          # user spoke -> THINKING, deadline pushed
    assert fsm.state == State.THINKING
    fsm.on_reply_done(now=116.0)         # bot finished -> LISTENING, deadline 136
    assert fsm.tick(now=135.0) == State.LISTENING
    assert fsm.tick(now=136.0) == State.SLEEPING


def test_speaking_cycle():
    fsm = DialogFSM(timeout=20)
    fsm.on_wake(now=0.0)
    fsm.on_utterance(now=1.0)
    fsm.on_reply_start()
    assert fsm.state == State.SPEAKING
    fsm.on_reply_done(now=3.0)
    assert fsm.state == State.LISTENING
