from conftest import PERSONA, TOUR
from typer.testing import CliRunner

from virtuguide.cli import app

runner = CliRunner()


def test_validate_ok():
    r = runner.invoke(app, ["validate", "-t", str(TOUR), "-p", str(PERSONA)])
    assert r.exit_code == 0, r.output
    assert r.output.count("ok") == 2


def test_validate_fails(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("id: x\n")
    r = runner.invoke(app, ["validate", "-t", str(bad)])
    assert r.exit_code == 1


def test_plan(tmp_path):
    r = runner.invoke(app, ["plan", str(TOUR), str(PERSONA), "--model", "ollama:m",
                            "--cache", str(tmp_path)])
    assert r.exit_code == 0, r.output
    assert "14 jobs, 14 to generate, ~1980 output words" in r.output


def test_plan_requires_model():
    assert runner.invoke(app, ["plan", str(TOUR), str(PERSONA)]).exit_code != 0


def test_plan_rejects_bad_model(tmp_path):
    r = runner.invoke(app, ["plan", str(TOUR), str(PERSONA), "--model", "nope"])
    assert r.exit_code != 0
