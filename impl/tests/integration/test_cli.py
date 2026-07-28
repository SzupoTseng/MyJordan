from __future__ import annotations

import json
from pathlib import Path

import pytest

from railway_core import settings as settings_mod
from railway_core.app import main


@pytest.fixture(autouse=True)
def isolated_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(settings_mod.ENV_DATA_DIR, str(tmp_path / "data"))
    monkeypatch.setenv(settings_mod.ENV_OUT_DIR, str(tmp_path / "out"))


def test_env_example_covers_every_env_var() -> None:
    """程式讀的每個環境變數,.env.example 都必須提到。

    漏掉的後果是:使用者永遠不知道有這個開關,而預設值出錯時無從查起。
    """
    example = (Path(__file__).resolve().parents[2] / ".env.example").read_text(encoding="utf-8")
    for name in settings_mod.ENV_VARS:
        assert name in example, f".env.example 缺少 {name}"


def test_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in settings_mod.ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    cfg = settings_mod.load()
    assert cfg.data_dir == Path("data")
    assert cfg.profile_code == "J"
    assert cfg.records_path.name == "records.jsonl"
    assert cfg.profile_path.name == "profile.json"


def test_init_writes_profile(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["init", "--code", "J", "--stage", "S2", "--chain-level", "6"]) == 0
    data = json.loads((tmp_path / "data" / "profile.json").read_text(encoding="utf-8"))
    assert data["code"] == "J" and data["stage"] == "S2" and data["chain_level"] == 6
    assert "附錄D" in capsys.readouterr().out


def test_init_rejects_name_like_code(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["init", "--code", "王小明同學本人"]) == 2
    assert "錯誤" in capsys.readouterr().err


def test_record_and_report(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["record", "--date", "2026-03-02", "--recovery", "300",
                 "--tasks", "4/1", "--sleep", "8"]) == 0
    assert main(["record", "--date", "2026-03-09", "--recovery", "120",
                 "--tasks", "4/3", "--sleep", "8", "--note", "睡得好"]) == 0
    assert main(["report", "--days", "7"]) == 0
    out = capsys.readouterr().out
    assert "週報" in out and "獨立完成率" in out


def test_report_without_records(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["report"]) == 0
    assert "第 1 章" in capsys.readouterr().out


def test_record_rejects_bad_tasks_format(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["record", "--date", "2026-03-02", "--tasks", "5"]) == 2
    assert "5/2" in capsys.readouterr().err


def test_record_rejects_bad_date(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["record", "--date", "03/02/2026"]) == 2


def test_gate_returns_nonzero_when_blocked(capsys: pytest.CaptureFixture[str]) -> None:
    main(["init", "--code", "J", "--stage", "S1"])
    main(["record", "--date", "2026-03-02", "--recovery", "400", "--tasks", "4/1"])
    assert main(["gate", "S1"]) == 1
    assert "留站" in capsys.readouterr().out


def test_gate_passes_with_manual_metrics(capsys: pytest.CaptureFixture[str]) -> None:
    main(["init", "--code", "J", "--stage", "S1"])
    for day in ("2026-03-02", "2026-03-03", "2026-03-04"):
        main(["record", "--date", day, "--recovery", "100", "--tasks", "4/3"])
    assert main(["gate", "S1", "--set", "gesture_stop_rate=0.9"]) == 0
    assert "可進入 S2" in capsys.readouterr().out


def test_gate_rejects_bad_set_syntax(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["gate", "S1", "--set", "gesture_stop_rate"]) == 2


def test_gate_reports_foundation_block(capsys: pytest.CaptureFixture[str]) -> None:
    main(["record", "--date", "2026-03-02", "--recovery", "100", "--tasks", "4/4"])
    code = main(["gate", "S1", "--set", "gesture_stop_rate=0.9", "--foundation", "剛調藥"])
    assert code == 1
    assert "剛調藥" in capsys.readouterr().out


def test_drill_prints_answers_by_default(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["drill", "M01", "--count", "2", "--seed", "1"]) == 0
    out = capsys.readouterr().out
    assert "答：" in out and "15 分鐘" in out


def test_drill_child_version_hides_answers(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["drill", "M01", "--count", "2", "--seed", "1", "--no-answer"]) == 0
    assert "答：" not in capsys.readouterr().out


def test_drill_m10_is_rejected(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["drill", "M10"]) == 2


def test_assets_written(tmp_path: Path) -> None:
    assert main(["assets"]) == 0
    produced = {p.name for p in (tmp_path / "out").glob("*.svg")}
    from railway_core.visuals import ASSET_FILENAMES
    assert produced == set(ASSET_FILENAMES)


def test_assets_custom_tasks(tmp_path: Path) -> None:
    assert main(["assets", "--tasks", "掃地", "拖地"]) == 0
    content = (tmp_path / "out" / "checklist_card.svg").read_text(encoding="utf-8")
    assert "掃地" in content and "拖地" in content


def test_assets_too_many_tasks_fails_cleanly() -> None:
    assert main(["assets", "--tasks", "a", "b", "c", "d", "e", "f"]) == 2


def test_listing_commands(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["stages"]) == 0
    assert main(["materials"]) == 0
    assert main(["redflags"]) == 0
    out = capsys.readouterr().out
    assert "S6" in out and "M10" in out and "停藥" in out


def test_no_subcommand_exits() -> None:
    with pytest.raises(SystemExit):
        main([])
