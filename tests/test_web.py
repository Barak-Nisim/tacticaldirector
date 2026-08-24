from fastapi.testclient import TestClient

from tacticaldirector.loader import load_encounter
from tacticaldirector.web.app import app

client = TestClient(app)

SAMPLE_ENCOUNTER = load_encounter("examples/sample_encounter.yaml")


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
    assert "Try the live demo" in response.text
    assert "How it works" in response.text
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
    assert "Tactical Recommendation" in response.text
    assert SAMPLE_ENCOUNTER.character.name in response.text
    assert "Ranked actions" in response.text
    assert "2.75 / 4.0" in response.text
    # no AI requested -> no Game Master's take section
    assert "gm-take" not in response.text


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
    assert "Ranked actions" in response.text


def test_advise_ai_checkbox_ignored_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    response = client.post("/advise", data=_sample_form_data(use_ai="1"))

    assert response.status_code == 200
    assert "Game Master's take" not in response.text


def test_report_includes_view_as_yaml_engineering_section():
    response = client.post("/advise", data=_sample_form_data())

    assert "View as YAML" in response.text
    assert f"name: {SAMPLE_ENCOUNTER.character.name}" in response.text
