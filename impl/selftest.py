#!/usr/bin/env python3
"""零依賴自測(標準庫 unittest)。

【WHY 除了 pytest 還要有這一支】
完整測試套件(tests/)需要 pytest + pytest-cov,而本書的讀者是家長——
他們的電腦上很可能沒有 pip、沒有 venv、也不打算安裝。
這一支用標準庫的 unittest 涵蓋主要路徑,讓「什麼都沒裝」的環境
也能在三秒內確認工具是好的:

    python3 selftest.py

CI 仍然跑完整的 pytest 套件與覆蓋率門檻;這一支是煙霧測試,不是替代品。
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from railway_core import behavior, curriculum, gate, safety, stages, tracking, visuals  # noqa: E402
from railway_core import settings as settings_mod  # noqa: E402
from railway_core.app import main  # noqa: E402
from railway_core.schemas import DailyRecord, Profile, ValidationError  # noqa: E402


class TestSchemas(unittest.TestCase):
    def test_profile_blocks_name_like_code(self) -> None:
        with self.assertRaises(ValidationError):
            Profile(code="王小明同學本人", stage="S1")

    def test_record_rejects_impossible_counts(self) -> None:
        with self.assertRaises(ValidationError):
            DailyRecord(date=dt.date(2026, 3, 2), tasks_total=1, tasks_independent=2)

    def test_no_task_day_is_none_not_zero(self) -> None:
        self.assertIsNone(DailyRecord(date=dt.date(2026, 3, 2)).independent_rate)


class TestStagesAndGate(unittest.TestCase):
    def test_all_criteria_metrics_registered(self) -> None:
        self.assertLessEqual(stages.metric_names(), tracking.metric_names())

    def test_gate_pass_and_fail(self) -> None:
        ok = gate.evaluate("S1", {"emotion_recovery_seconds": 100,
                                  "independent_task_rate": 0.8,
                                  "gesture_stop_rate": 0.9})
        self.assertTrue(ok.passed)
        self.assertIn("可進入 S2", gate.render(ok))

        blocked = gate.evaluate("S1", {}, caregiver_flags=3)
        self.assertFalse(blocked.passed)
        self.assertIn("照顧者門", blocked.blocked_by)

    def test_unknown_metric_raises(self) -> None:
        with self.assertRaises(KeyError):
            gate.evaluate("S1", {"typo_metric": 1})

    # 以下四項是 scripts/mutation_sweep.py 找出來的破口:
    # 原本 selftest 對它們毫無反應,而它們每一個壞掉都會讓「留站」變成「放行」。

    def test_empty_criteria_is_not_a_pass(self) -> None:
        """all([]) 是 True——空的標準清單不可以被判為通過。"""
        from railway_core.schemas import GateResult
        self.assertFalse(GateResult(stage="S1").ability_ok)

    def test_unmeasured_metric_never_passes(self) -> None:
        """沒量到就是沒過。附錄C 的頭號反模式:為了進度而放寬標準。"""
        criterion = stages.Criterion("m", "標籤", 0, ">=", "", 14, ("家",))
        self.assertFalse(criterion.check(None))

    def test_criterion_requires_week_long_window(self) -> None:
        with self.assertRaises(ValueError):
            stages.Criterion("m", "標籤", 1, ">=", "", 3, ("家",))

    def test_criterion_requires_domains(self) -> None:
        with self.assertRaises(ValueError):
            stages.Criterion("m", "標籤", 1, ">=", "", 14, ())


class TestCurriculum(unittest.TestCase):
    def test_ten_materials(self) -> None:
        self.assertEqual(len(curriculum.all_materials()), 10)

    def test_seed_reproducible(self) -> None:
        a = [q.prompt for q in curriculum.generate("M04", 4, seed=9)]
        b = [q.prompt for q in curriculum.generate("M04", 4, seed=9)]
        self.assertEqual(a, b)

    def test_m10_has_no_drill(self) -> None:
        with self.assertRaises(ValueError):
            curriculum.generate("M10", 1)

    def test_m04_answer_is_sufficient(self) -> None:
        for q in curriculum.generate("M04", 10, seed=5):
            price = int(q.prompt.split("門票要 ")[1].split(" 元")[0])
            self.assertGreaterEqual(int(q.answer.split(" ")[0]), price)

    def test_count_is_capped(self) -> None:
        """第 21 章:每次不超過 15 分鐘。上限不設,教材就會變成折磨。"""
        with self.assertRaises(ValueError):
            curriculum.generate("M01", 99)


class TestTracking(unittest.TestCase):
    def test_summary_weights_by_total_tasks(self) -> None:
        records = [
            DailyRecord(date=dt.date(2026, 3, 1), tasks_total=1, tasks_independent=1),
            DailyRecord(date=dt.date(2026, 3, 2), tasks_total=10, tasks_independent=2),
        ]
        rate = tracking.summarize(records).independent_task_rate
        assert rate is not None
        self.assertAlmostEqual(rate, 3 / 11)

    def test_latest_anchors_on_last_record_not_today(self) -> None:
        """基準是最後一筆的日期。取錯端點,「最近 N 天」會拿到最舊的資料。"""
        with tempfile.TemporaryDirectory() as tmp:
            store = tracking.RecordStore(Path(tmp) / "r.jsonl")
            base = dt.date(2020, 1, 1)
            for i in range(10):
                store.append(DailyRecord(date=base + dt.timedelta(days=i),
                                         emotion_recovery_seconds=100 + i))
            latest = store.latest(3)
            self.assertEqual(len(latest), 3)
            self.assertEqual(latest[-1].date, base + dt.timedelta(days=9))

    def test_store_sorts_and_survives_blank_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = tracking.RecordStore(Path(tmp) / "r.jsonl")
            store.append(DailyRecord(date=dt.date(2026, 3, 5)))
            store.append(DailyRecord(date=dt.date(2026, 3, 1)))
            with store.path.open("a", encoding="utf-8") as handle:
                handle.write("\n")
            dates = [r.date for r in store.all()]
            self.assertEqual(dates, sorted(dates))


class TestSafetyAndVisuals(unittest.TestCase):
    def test_red_flags_present(self) -> None:
        self.assertGreaterEqual(len(safety.RED_FLAGS), 8)
        self.assertTrue(any("停藥" in item for item in safety.NEVER_DO))

    def test_scan_detects_sleep_debt(self) -> None:
        records = [DailyRecord(date=dt.date(2026, 3, i + 1), sleep_hours=5.0)
                   for i in range(14)]
        self.assertIn("sleep_debt", {s.key for s in safety.scan(records)})

    def test_scan_stays_quiet_without_a_week(self) -> None:
        """不足一週就下判斷,只會產生雜訊等級的警告,然後家長就不再看它了。"""
        records = [DailyRecord(date=dt.date(2026, 3, i + 1), sleep_hours=4.0)
                   for i in range(6)]
        self.assertEqual(safety.scan(records), [])

    def test_checklist_escapes_and_caps(self) -> None:
        asset = visuals.checklist_card(["擦 <黑板> & 桌子"])
        self.assertIn("&lt;黑板&gt;", asset.content)
        with self.assertRaises(ValueError):
            visuals.checklist_card(["a", "b", "c", "d", "e", "f"])

    def test_task_analysis_card(self) -> None:
        asset = visuals.task_analysis_card(["攤平", "對折", "壓平"])
        self.assertIn("對折", asset.content)
        self.assertEqual(asset.filename, "task_analysis_card.svg")
        with self.assertRaises(ValueError):
            visuals.task_analysis_card([f"步驟{i}" for i in range(13)])
        with self.assertRaises(ValueError):
            visuals.task_analysis_card([])

    def test_record_forms(self) -> None:
        """四張記錄表：能產生、有邊界檢查、且帶著書裡的提醒。"""
        self.assertIn("三分鐘", visuals.daily_log().content)
        self.assertIn("他因此得到了什麼", visuals.abc_form().content)
        self.assertIn("夜間發作", visuals.sleep_log().content)
        self.assertIn("非物品", visuals.preference_form().content)
        for bad in (lambda: visuals.daily_log(days=40),
                    lambda: visuals.abc_form(rows=100),
                    lambda: visuals.sleep_log(days=3),
                    lambda: visuals.preference_form(["a", "b"])):
            with self.assertRaises(ValueError):
                bad()

    def test_assets_are_self_contained(self) -> None:
        for asset in (visuals.checklist_card(["a"]), visuals.token_board(),
                      visuals.price_cards([("a", 1)]),
                      visuals.task_analysis_card(["a"]),
                      visuals.timetable_card([("13:00", "a")]),
                      visuals.daily_log(), visuals.abc_form(),
                      visuals.sleep_log(), visuals.preference_form()):
            # xmlns 的 http://www.w3.org/2000/svg 是命名空間宣告,不是外部資源,
            # 檢查前先移除,否則會永遠誤判。
            body = asset.content.replace('xmlns="http://www.w3.org/2000/svg"', "")
            self.assertNotIn("http", body)
            self.assertNotIn("<image", body)
            self.assertTrue(asset.content.startswith("<svg"))


class TestBehavior(unittest.TestCase):
    def _record(self, **kwargs: object) -> behavior.AbcRecord:
        base: dict[str, object] = {
            "date": dt.date(2026, 3, 2), "time": "16:20",
            "antecedent": "剛被要求收玩具", "behavior": "重複說火車、音量提高",
            "consequence": "我幫他收了玩具", "hypothesis": "escape",
        }
        base.update(kwargs)
        return behavior.AbcRecord(**base)  # type: ignore[arg-type]

    def test_a_and_c_are_required(self) -> None:
        for field in ("antecedent", "consequence"):
            with self.assertRaises(ValidationError):
                self._record(**{field: "   "})

    def test_vague_answers_are_rejected(self) -> None:
        """「不知道」幾乎總是代表「當時沒看到」——留著它，記錄就廢了。"""
        for vague in ("不知道", "沒有原因", "突然就"):
            with self.assertRaises(ValidationError):
                self._record(antecedent=vague)

    def test_bad_time_and_function(self) -> None:
        with self.assertRaises(ValidationError):
            self._record(time="16.20")
        with self.assertRaises(ValidationError):
            self._record(hypothesis="revenge")

    def test_no_conclusion_below_threshold(self) -> None:
        """不足 10 筆不下結論：那是最近一次事件的印象，不是型態。

        【WHY 這裡寫死 9 與 10，而不是用 MIN_RECORDS_FOR_HYPOTHESIS ± 1】
        用常數自己去測那個常數，等於什麼都沒測——把 10 改成 1，測試照樣通過。
        這個洞是 scripts/mutation_sweep.py 抓出來的。
        門檻 10 來自第 35 章（連續兩週、至少 10 筆），它是規格，所以寫死。
        """
        self.assertEqual(behavior.MIN_RECORDS_FOR_HYPOTHESIS, 10)
        self.assertFalse(behavior.summarize_functions(
            [self._record() for _ in range(9)]).enough_data)
        summary = behavior.summarize_functions([self._record() for _ in range(10)])
        self.assertTrue(summary.enough_data)
        self.assertEqual(summary.top, "escape")

    def test_hypothesis_sentence_and_strategy(self) -> None:
        sentence = behavior.hypothesis_sentence("被要求結束活動", "重複同一句話", "escape")
        self.assertIn("以逃避", sentence)
        do, dont = behavior.strategy_for("sensory")
        self.assertTrue(any("替代感官" in item for item in do))
        self.assertTrue(any("無效" in item for item in dont))

    def test_store_roundtrip_and_sort(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = behavior.AbcStore(Path(tmp) / "abc.jsonl")
            store.append(self._record(time="18:00"))
            store.append(self._record(time="09:00"))
            times = [r.time for r in store.all()]
            self.assertEqual(times, sorted(times))


class TestCli(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._old = {name: os.environ.get(name) for name in settings_mod.ENV_VARS}
        os.environ[settings_mod.ENV_DATA_DIR] = str(Path(self._tmp.name) / "data")
        os.environ[settings_mod.ENV_OUT_DIR] = str(Path(self._tmp.name) / "out")

    def tearDown(self) -> None:
        for name, value in self._old.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        self._tmp.cleanup()

    def test_full_flow(self) -> None:
        self.assertEqual(main(["init", "--code", "J", "--stage", "S1"]), 0)
        profile = json.loads((Path(self._tmp.name) / "data" / "profile.json")
                             .read_text(encoding="utf-8"))
        self.assertEqual(profile["code"], "J")

        self.assertEqual(main(["record", "--date", "2026-03-02",
                               "--recovery", "100", "--tasks", "4/3"]), 0)
        self.assertEqual(main(["report", "--days", "7"]), 0)
        self.assertEqual(main(["gate", "S1", "--set", "gesture_stop_rate=0.9"]), 0)
        self.assertEqual(main(["drill", "M01", "--count", "2", "--seed", "1"]), 0)
        self.assertEqual(main(["assets"]), 0)

        produced = {p.name for p in (Path(self._tmp.name) / "out").glob("*.svg")}
        self.assertEqual(produced, set(visuals.ASSET_FILENAMES))

    def test_bad_input_returns_two(self) -> None:
        self.assertEqual(main(["record", "--date", "03/02/2026"]), 2)
        self.assertEqual(main(["record", "--date", "2026-03-02", "--tasks", "5"]), 2)

    def test_abc_flow(self) -> None:
        self.assertEqual(main([
            "abc", "--date", "2026-03-02", "--time", "16:20",
            "-a", "剛被要求收玩具", "-b", "重複說火車", "-c", "我幫他收了玩具",
            "--function", "escape",
        ]), 0)
        self.assertEqual(main(["function"]), 0)
        # A 欄填「不知道」要被擋下來
        self.assertEqual(main([
            "abc", "--date", "2026-03-02", "--time", "16:20",
            "-a", "不知道", "-b", "離座", "-c", "老師帶回座位",
        ]), 2)

    def test_env_example_covers_env_vars(self) -> None:
        example = (Path(__file__).resolve().parent / ".env.example").read_text(encoding="utf-8")
        for name in settings_mod.ENV_VARS:
            self.assertIn(name, example)


if __name__ == "__main__":
    unittest.main(verbosity=2)
