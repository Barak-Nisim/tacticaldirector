from tacticaldirector.play import scenarios as scenarios_module
from tacticaldirector.play.scenarios import list_scenarios, scenario_path


def test_list_scenarios_returns_empty_when_directory_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(scenarios_module, "SCENARIOS_DIR", tmp_path / "nope")

    assert list_scenarios() == []


def test_list_scenarios_uses_known_blurb_for_built_in_ids(monkeypatch, tmp_path):
    (tmp_path / "goblin_warcamp.yaml").write_text("placeholder", encoding="utf-8")
    monkeypatch.setattr(scenarios_module, "SCENARIOS_DIR", tmp_path)

    result = list_scenarios()

    assert len(result) == 1
    assert result[0]["id"] == "goblin_warcamp"
    assert result[0]["label"] == "Goblin Warcamp"
    assert result[0]["blurb"]


def test_list_scenarios_falls_back_to_a_title_cased_label_for_unknown_ids(monkeypatch, tmp_path):
    (tmp_path / "custom_encounter.yaml").write_text("placeholder", encoding="utf-8")
    monkeypatch.setattr(scenarios_module, "SCENARIOS_DIR", tmp_path)

    result = list_scenarios()

    assert result[0]["label"] == "Custom Encounter"
    assert result[0]["blurb"] == "A hand-crafted encounter."


def test_list_scenarios_is_sorted_by_id(monkeypatch, tmp_path):
    (tmp_path / "zzz.yaml").write_text("placeholder", encoding="utf-8")
    (tmp_path / "aaa.yaml").write_text("placeholder", encoding="utf-8")
    monkeypatch.setattr(scenarios_module, "SCENARIOS_DIR", tmp_path)

    result = list_scenarios()

    assert [s["id"] for s in result] == ["aaa", "zzz"]


def test_scenario_path_builds_a_yaml_path_under_the_scenarios_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(scenarios_module, "SCENARIOS_DIR", tmp_path)

    assert scenario_path("goblin_warcamp") == tmp_path / "goblin_warcamp.yaml"
