from tacticaldirector.loader import load_encounter
from tacticaldirector.play import resolution
from tacticaldirector.play.session import load_session, save_session, start_session


def _sample_encounter():
    return load_encounter("examples/sample_encounter.yaml")


def test_start_session_creates_and_persists_a_new_session(monkeypatch, tmp_path):
    monkeypatch.setenv("TACTICALDIRECTOR_SESSION_DIR", str(tmp_path))

    session = start_session("broken_bridge_ambush", _sample_encounter(), seed=1)

    assert session.status == "in_progress"
    assert session.round_log == ()
    assert (tmp_path / f"{session.session_id}.json").exists()


def test_load_session_returns_none_for_unknown_id(monkeypatch, tmp_path):
    monkeypatch.setenv("TACTICALDIRECTOR_SESSION_DIR", str(tmp_path))

    assert load_session("does-not-exist") is None


def test_save_and_load_round_trip_preserves_encounter_state(monkeypatch, tmp_path):
    monkeypatch.setenv("TACTICALDIRECTOR_SESSION_DIR", str(tmp_path))
    session = start_session("broken_bridge_ambush", _sample_encounter(), seed=1)

    loaded = load_session(session.session_id)

    assert loaded is not None
    assert loaded.session_id == session.session_id
    assert loaded.scenario_id == "broken_bridge_ambush"
    assert loaded.seed == 1
    assert loaded.encounter.character.name == session.encounter.character.name
    assert loaded.encounter.enemies == session.encounter.enemies
    assert loaded.status == "in_progress"


def test_save_and_load_round_trip_preserves_round_log(monkeypatch, tmp_path):
    import random
    from dataclasses import replace

    monkeypatch.setenv("TACTICALDIRECTOR_SESSION_DIR", str(tmp_path))
    session = start_session("broken_bridge_ambush", _sample_encounter(), seed=7)

    rng = random.Random(7)
    new_encounter, outcome, status = resolution.resolve_round(session.encounter, "attack", rng)
    updated = replace(
        session,
        encounter=new_encounter,
        round_log=session.round_log + (outcome,),
        status=status,
    )
    save_session(updated)

    loaded = load_session(session.session_id)

    assert len(loaded.round_log) == 1
    assert loaded.round_log[0].action == "attack"
    assert loaded.round_log[0].outcome_tier == outcome.outcome_tier
    assert loaded.status == status


def test_session_storage_is_isolated_from_real_user_home(monkeypatch, tmp_path):
    # defense-in-depth check, same as marketsignal's history isolation test:
    # confirm the env var override actually redirects storage away from the
    # real ~/.tacticaldirector, so tests can never write into a real home dir
    monkeypatch.setenv("TACTICALDIRECTOR_SESSION_DIR", str(tmp_path))

    session = start_session("goblin_warcamp", _sample_encounter(), seed=2)

    assert (tmp_path / f"{session.session_id}.json").exists()
