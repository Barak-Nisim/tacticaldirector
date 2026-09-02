import json

from tacticaldirector.cli import main
from tacticaldirector.play import scenarios as scenarios_module


def test_advise_no_ai_prints_report(capsys):
    exit_code = main(["advise", "examples/sample_encounter.yaml", "--no-ai"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "TacticalDirector Advisory: Kaelen" in captured.out
    assert "Recommended actions (ranked)" in captured.out


def test_advise_no_ai_writes_to_output_file(tmp_path):
    output_path = tmp_path / "report.md"
    exit_code = main(
        ["advise", "examples/sample_encounter.yaml", "--no-ai", "--output", str(output_path)]
    )

    assert exit_code == 0
    assert output_path.exists()
    assert "TacticalDirector Advisory" in output_path.read_text(encoding="utf-8")


def test_advise_includes_enemy_intelligence(capsys):
    exit_code = main(["advise", "examples/sample_encounter.yaml", "--no-ai"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Enemy intelligence" in captured.out
    assert "Orc Raider" in captured.out
    assert "Goblin Archer" in captured.out


def test_play_with_script_runs_to_completion_non_interactively(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("TACTICALDIRECTOR_SESSION_DIR", str(tmp_path))

    exit_code = main(
        [
            "play",
            "examples/sample_encounter.yaml",
            "--seed",
            "1",
            "--script",
            "attack,attack,attack,attack,attack",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Starting session" in captured.out
    assert "Session defeat. 3 round(s) played." in captured.out
    assert "After Action Report" in captured.out
    assert "Round 4" in captured.out  # sample_encounter.yaml starts at round_number 4
    assert "Enemy intelligence" in captured.out
    assert list(tmp_path.glob("*.json"))  # session was persisted


def test_play_rejects_unknown_action_and_keeps_going(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("TACTICALDIRECTOR_SESSION_DIR", str(tmp_path))

    exit_code = main(
        [
            "play",
            "examples/sample_encounter.yaml",
            "--seed",
            "1",
            "--script",
            "flee_screaming,attack,attack,attack,attack,attack",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Unknown action: flee_screaming" in captured.err
    assert "Session defeat. 3 round(s) played." in captured.out


def test_play_script_exhausted_ends_session_early(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("TACTICALDIRECTOR_SESSION_DIR", str(tmp_path))

    exit_code = main(
        ["play", "examples/sample_encounter.yaml", "--seed", "1", "--script", "attack"]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Script exhausted" in captured.err
    assert "Session in_progress." in captured.out


def test_play_narrate_attaches_gm_narration(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("TACTICALDIRECTOR_SESSION_DIR", str(tmp_path))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    seen_rounds = []

    def fake_narrate_round(session, outcome):
        seen_rounds.append(outcome.round_number)
        return {"gm_take": "Kaelen's blade bites deep.", "table_talk": "The torches gutter."}

    monkeypatch.setattr(
        "tacticaldirector.ai.round_narrator.narrate_round", fake_narrate_round
    )

    exit_code = main(
        [
            "play",
            "examples/sample_encounter.yaml",
            "--seed",
            "1",
            "--script",
            "attack,attack,attack,attack,attack",
            "--narrate",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert seen_rounds  # the narrator was actually called
    assert "-- GM --" in captured.out
    assert "Kaelen's blade bites deep." in captured.out
    assert "The torches gutter." in captured.out

    saved = json.loads(next(tmp_path.glob("*.json")).read_text(encoding="utf-8"))
    assert saved["narrate"] is True
    assert any(r.get("gm_narration") for r in saved["round_log"])


def test_play_narrate_without_api_key_warns_and_continues(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("TACTICALDIRECTOR_SESSION_DIR", str(tmp_path))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    exit_code = main(
        [
            "play",
            "examples/sample_encounter.yaml",
            "--seed",
            "1",
            "--script",
            "attack,attack,attack,attack,attack",
            "--narrate",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "without GM narration" in captured.err
    assert "-- GM --" not in captured.out
    assert "Session defeat. 3 round(s) played." in captured.out


def test_play_narrate_survives_a_narrator_failure(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("TACTICALDIRECTOR_SESSION_DIR", str(tmp_path))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    def boom(session, outcome):
        raise RuntimeError("api down")

    monkeypatch.setattr("tacticaldirector.ai.round_narrator.narrate_round", boom)

    exit_code = main(
        [
            "play",
            "examples/sample_encounter.yaml",
            "--seed",
            "1",
            "--script",
            "attack,attack,attack,attack,attack",
            "--narrate",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "GM narration unavailable this round: api down" in captured.err
    assert "Session defeat. 3 round(s) played." in captured.out


def test_scenarios_lists_yaml_files_when_present(monkeypatch, tmp_path, capsys):
    (tmp_path / "goblin_warcamp.yaml").write_text("placeholder", encoding="utf-8")
    (tmp_path / "lone_sentinel.yaml").write_text("placeholder", encoding="utf-8")
    monkeypatch.setattr(scenarios_module, "SCENARIOS_DIR", tmp_path)

    exit_code = main(["scenarios"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "goblin_warcamp" in captured.out
    assert "lone_sentinel" in captured.out


def test_scenarios_with_missing_directory_prints_helpful_message(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(scenarios_module, "SCENARIOS_DIR", tmp_path / "does-not-exist")

    exit_code = main(["scenarios"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "No scenarios found" in captured.err
