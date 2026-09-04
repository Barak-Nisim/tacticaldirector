import shutil

from fastapi.testclient import TestClient

from tacticaldirector.loader import load_encounter
from tacticaldirector.play import scenarios as scenarios_module
from tacticaldirector.web.app import app

client = TestClient(app)

SAMPLE_ENCOUNTER = load_encounter("examples/sample_encounter.yaml")


def _isolated_scenarios_dir(monkeypatch, tmp_path):
    scenarios_dir = tmp_path / "scenarios"
    scenarios_dir.mkdir()
    shutil.copy("examples/sample_encounter.yaml", scenarios_dir / "broken_bridge_ambush.yaml")
    monkeypatch.setattr(scenarios_module, "SCENARIOS_DIR", scenarios_dir)
    return scenarios_dir


def _sample_form_data(**overrides):
    c = SAMPLE_ENCOUNTER.character
    data = {
        "name": c.name,
        "archetype": c.archetype,
        "level": str(c.level),
        "hp_current": str(c.hp_current),
        "hp_max": str(c.hp_max),
        "resources_current": str(c.resources_current),
        "resources_max": str(c.resources_max),
        "round_number": str(SAMPLE_ENCOUNTER.round_number),
    }
    for i, enemy in enumerate(SAMPLE_ENCOUNTER.enemies):
        data[f"enemy_name_{i}"] = enemy.name
        data[f"enemy_threat_{i}"] = str(enemy.threat_tier)
    if SAMPLE_ENCOUNTER.terrain.high_ground:
        data["high_ground"] = "1"
    if SAMPLE_ENCOUNTER.terrain.cover:
        data["cover"] = "1"
    if SAMPLE_ENCOUNTER.terrain.hazard:
        data["hazard"] = "1"
    data.update(overrides)
    return data


def test_landing_page_shows_marketing_content():
    response = client.get("/")

    assert response.status_code == 200
    assert "TacticalDirector" in response.text
    assert "Consult the Codex" in response.text
    assert "How it works" in response.text
    assert "Warrior" in response.text and "Mage" in response.text
    assert 'name="hp_current"' not in response.text


def test_how_it_works_page_explains_methodology():
    response = client.get("/how-it-works")

    assert response.status_code == 200
    assert "How TacticalDirector works" in response.text
    assert "Offensive Value" in response.text


def test_app_form_is_prefilled_from_sample_encounter():
    response = client.get("/app")

    assert response.status_code == 200
    assert "<form" in response.text
    assert SAMPLE_ENCOUNTER.character.name in response.text
    assert "Orc Raider" in response.text
    assert 'name="archetype"' in response.text


def test_advise_renders_ranked_report_from_structured_form():
    response = client.post("/advise", data=_sample_form_data())

    assert response.status_code == 200
    assert "The Codex Speaks" in response.text
    assert SAMPLE_ENCOUNTER.character.name in response.text
    assert "The Codex's Verdict" in response.text
    assert "2.75 / 4.0" in response.text
    # no AI requested -> no Game Master's take section
    assert "gm-take" not in response.text


def test_advise_shows_enemy_intelligence():
    response = client.post("/advise", data=_sample_form_data())

    assert response.status_code == 200
    assert "Enemy intelligence" in response.text
    assert "Orc Raider" in response.text


def test_advise_with_no_enemies_still_scores():
    response = client.post(
        "/advise",
        data={
            "name": "Solo",
            "archetype": "warrior",
            "level": "1",
            "hp_current": "10",
            "hp_max": "10",
            "resources_current": "0",
            "resources_max": "0",
            "round_number": "1",
        },
    )

    assert response.status_code == 200
    assert "Solo" in response.text
    assert "The Codex's Verdict" in response.text
    assert "Enemy intelligence" not in response.text


def test_advise_ai_checkbox_ignored_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    response = client.post("/advise", data=_sample_form_data(use_ai="1"))

    assert response.status_code == 200
    assert "Game Master's take" not in response.text


def test_report_includes_view_as_yaml_engineering_section():
    response = client.post("/advise", data=_sample_form_data())

    assert "View as YAML" in response.text
    assert f"name: {SAMPLE_ENCOUNTER.character.name}" in response.text


# ---------- Play Mode ----------


def test_play_page_lists_scenarios(monkeypatch, tmp_path):
    _isolated_scenarios_dir(monkeypatch, tmp_path)

    response = client.get("/play")

    assert response.status_code == 200
    assert "Broken Bridge Ambush" in response.text


def test_play_page_shows_empty_state_when_no_scenarios(monkeypatch, tmp_path):
    monkeypatch.setattr(scenarios_module, "SCENARIOS_DIR", tmp_path / "nope")

    response = client.get("/play")

    assert response.status_code == 200
    assert "No scenarios are available yet" in response.text


def test_play_page_offers_a_visible_seed_field(monkeypatch, tmp_path):
    _isolated_scenarios_dir(monkeypatch, tmp_path)

    response = client.get("/play")

    assert response.status_code == 200
    assert 'id="play-seed"' in response.text
    assert 'name="seed"' in response.text  # the hidden field each card form submits


def test_play_start_with_blank_seed_falls_back_to_a_random_one(monkeypatch, tmp_path):
    _isolated_scenarios_dir(monkeypatch, tmp_path)
    monkeypatch.setenv("TACTICALDIRECTOR_SESSION_DIR", str(tmp_path / "sessions"))
    from tacticaldirector.play.session import load_session

    response = client.post(
        "/play/start",
        data={"scenario": "broken_bridge_ambush", "seed": ""},
        follow_redirects=False,
    )

    assert response.status_code == 303
    session_id = response.headers["location"].removeprefix("/play/")
    session = load_session(session_id)
    assert isinstance(session.seed, int)


def test_play_start_with_a_malformed_seed_does_not_500(monkeypatch, tmp_path):
    _isolated_scenarios_dir(monkeypatch, tmp_path)
    monkeypatch.setenv("TACTICALDIRECTOR_SESSION_DIR", str(tmp_path / "sessions"))
    from tacticaldirector.play.session import load_session

    response = client.post(
        "/play/start",
        data={"scenario": "broken_bridge_ambush", "seed": "not-a-number"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    session_id = response.headers["location"].removeprefix("/play/")
    session = load_session(session_id)
    assert isinstance(session.seed, int)  # fell back to a random seed, not a crash


def test_play_start_creates_session_and_redirects(monkeypatch, tmp_path):
    _isolated_scenarios_dir(monkeypatch, tmp_path)
    monkeypatch.setenv("TACTICALDIRECTOR_SESSION_DIR", str(tmp_path / "sessions"))

    response = client.post(
        "/play/start",
        data={"scenario": "broken_bridge_ambush", "seed": "1"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"].startswith("/play/")
    assert list((tmp_path / "sessions").glob("*.json"))


def test_play_round_shows_ranking_for_in_progress_session(monkeypatch, tmp_path):
    _isolated_scenarios_dir(monkeypatch, tmp_path)
    monkeypatch.setenv("TACTICALDIRECTOR_SESSION_DIR", str(tmp_path / "sessions"))

    response = client.post("/play/start", data={"scenario": "broken_bridge_ambush", "seed": "1"})

    assert response.status_code == 200
    assert "The Codex's Verdict" in response.text
    assert SAMPLE_ENCOUNTER.character.name in response.text
    assert "Take this action" in response.text
    assert "Enemy intelligence" in response.text
    assert "Orc Raider" in response.text


def test_play_round_returns_404_for_unknown_session(monkeypatch, tmp_path):
    monkeypatch.setenv("TACTICALDIRECTOR_SESSION_DIR", str(tmp_path / "sessions"))

    response = client.get("/play/does-not-exist")

    assert response.status_code == 404
    assert "not found" in response.text.lower()


def test_play_act_resolves_a_round_and_shows_the_outcome(monkeypatch, tmp_path):
    _isolated_scenarios_dir(monkeypatch, tmp_path)
    monkeypatch.setenv("TACTICALDIRECTOR_SESSION_DIR", str(tmp_path / "sessions"))

    start_response = client.post(
        "/play/start", data={"scenario": "broken_bridge_ambush", "seed": "1"}
    )
    session_id = start_response.url.path.rsplit("/", 1)[-1]

    act_response = client.post(f"/play/{session_id}/act", data={"action": "attack"})

    assert act_response.status_code == 200
    assert "Round 4: Attack" in act_response.text
    assert "<dt>Rounds played</dt><dd>1</dd>" in act_response.text


def test_full_scripted_playthrough_reaches_a_terminal_status(monkeypatch, tmp_path):
    _isolated_scenarios_dir(monkeypatch, tmp_path)
    monkeypatch.setenv("TACTICALDIRECTOR_SESSION_DIR", str(tmp_path / "sessions"))

    start_response = client.post(
        "/play/start", data={"scenario": "broken_bridge_ambush", "seed": "1"}
    )
    session_id = start_response.url.path.rsplit("/", 1)[-1]

    response = start_response
    for _ in range(30):
        if "Take this action" not in response.text:
            break
        response = client.post(f"/play/{session_id}/act", data={"action": "attack"})

    assert "Play again" in response.text
    assert any(f"Session {label}" in response.text for label in ("Victory", "Defeat", "Retreated"))
    assert "After Action Report" in response.text
    assert "Round 4" in response.text  # sample_encounter.yaml starts at round_number 4
