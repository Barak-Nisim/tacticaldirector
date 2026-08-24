from tacticaldirector.cli import main


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
