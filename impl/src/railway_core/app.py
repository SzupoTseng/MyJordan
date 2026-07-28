"""CLI:railway。

用法（在 impl/ 目錄下）:
    python -m railway_core.app init
    python -m railway_core.app record --date 2026-03-02 --recovery 190 --tasks 5/2 --sleep 7.5
    python -m railway_core.app report
    python -m railway_core.app gate S1 --set gesture_stop_rate=0.82
    python -m railway_core.app drill M04 --count 8 --seed 7
    python -m railway_core.app assets
    python -m railway_core.app redflags
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import behavior, curriculum, gate, safety, stages, tracking, visuals
from . import settings as settings_mod
from .schemas import DailyRecord, Profile, ValidationError, parse_date


def _store(cfg: settings_mod.Settings) -> tracking.RecordStore:
    return tracking.RecordStore(cfg.records_path)


def _load_profile(cfg: settings_mod.Settings) -> Profile:
    if cfg.profile_path.exists():
        return Profile.from_dict(json.loads(cfg.profile_path.read_text(encoding="utf-8")))
    return Profile(code=cfg.profile_code, stage="S1",
                   fixation_topic=cfg.fixation_topic, role_title=cfg.role_title)


def cmd_init(args: argparse.Namespace, cfg: settings_mod.Settings) -> int:
    profile = Profile(
        code=args.code or cfg.profile_code,
        stage=args.stage,
        fixation_topic=args.topic or cfg.fixation_topic,
        role_title=args.role or cfg.role_title,
        chain_level=args.chain_level,
    )
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    cfg.profile_path.write_text(
        json.dumps(profile.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已建立 {cfg.profile_path}")
    print(f"代號 {profile.code}／站別 {profile.stage}／角色 {profile.role_title}"
          f"／主題 {profile.fixation_topic}")
    print("★ 真實姓名、校名、醫院名請寫在附錄D 的私人檔，不要放進這裡。")
    return 0


def _parse_tasks(value: str | None) -> tuple[int, int]:
    if not value:
        return 0, 0
    if "/" not in value:
        raise ValidationError("--tasks 請用 總數/獨立完成數，例如 5/2")
    total_text, independent_text = value.split("/", 1)
    return int(total_text), int(independent_text)


def cmd_record(args: argparse.Namespace, cfg: settings_mod.Settings) -> int:
    total, independent = _parse_tasks(args.tasks)
    record = DailyRecord(
        date=parse_date(args.date),
        emotion_recovery_seconds=args.recovery,
        tasks_total=total,
        tasks_independent=independent,
        chain_steps_ok=args.chain,
        fixation_talk_minutes=args.fixation,
        fixation_structured=args.structured,
        sleep_hours=args.sleep,
        note=args.note or "",
    )
    _store(cfg).append(record)
    print(f"已記錄 {record.date}")
    return 0


def cmd_report(args: argparse.Namespace, cfg: settings_mod.Settings) -> int:
    store = _store(cfg)
    records = store.all()
    if not records:
        print("還沒有任何記錄。先做第 1 章的兩週基線：每天不超過三分鐘。")
        return 0

    window = args.days
    recent = store.latest(window)
    # 【WHY 用日期集合切分,而不是「不在 recent 裡」】
    # 同一天可能有多筆記錄(兩位照顧者各記各的),用物件比對會把重複的那筆
    # 誤判到前期,讓兩段期間的比較失真。切分的單位是「日期」,不是「筆」。
    recent_dates = {r.date for r in recent}
    previous = tracking.summarize([r for r in records if r.date not in recent_dates])
    current = tracking.summarize(recent)

    print(f"週報　最近 {window} 天（{current.samples} 筆記錄）")
    print("─" * 56)
    print(f"情緒回復時間（中位數）：{_fmt(current.emotion_recovery_median)} 秒"
          f"　最差 {_fmt(current.emotion_recovery_worst)} 秒")
    print(f"獨立完成率：{_fmt(current.independent_task_rate, 2)}")
    print(f"指令步數（最佳）：{_fmt(current.chain_steps_max)}")
    print(f"固著話題（中位數）：{_fmt(current.fixation_talk_median)} 分"
          f"　結構化比率 {_fmt(current.fixation_structured_ratio, 2)}")
    print(f"睡眠（中位數）：{_fmt(current.sleep_median, 1)} 小時"
          f"　不足 7 小時：{current.low_sleep_days} 天")
    print("─" * 56)
    for line in tracking.trend(previous, current):
        print(f"· {line}")

    signals = safety.scan(records)
    if signals:
        print("─" * 56)
        print("值得回頭看一眼（不是診斷）：")
        for signal in signals:
            print(f"⚠️ {signal.message}")
    return 0


def _fmt(value: float | int | None, digits: int = 0) -> str:
    if value is None:
        return "—"
    return f"{value:.{digits}f}"


def cmd_gate(args: argparse.Namespace, cfg: settings_mod.Settings) -> int:
    store = _store(cfg)
    profile = _load_profile(cfg)
    summary = tracking.summarize(store.latest(args.days))
    metrics = summary.as_metrics()
    metrics["chain_level"] = float(profile.chain_level)

    for item in args.set or []:
        if "=" not in item:
            raise ValidationError(f"--set 請用 指標=數值，收到 {item!r}")
        key, raw = item.split("=", 1)
        metrics[key.strip()] = float(raw)

    result = gate.evaluate(
        args.stage,
        metrics,
        foundation_notes=args.foundation or [],
        caregiver_flags=args.caregiver_flags,
    )
    print(gate.render(result))
    return 0 if result.passed else 1


def cmd_drill(args: argparse.Namespace, cfg: settings_mod.Settings) -> int:
    profile = _load_profile(cfg)
    questions = curriculum.generate(args.material, count=args.count,
                                    seed=args.seed, role=profile.role_title)
    material = curriculum.get_material(args.material)
    print(f"{material.code}　{material.name}（{curriculum.DIMENSIONS[material.dimension]}"
          f"・第 {material.chapter} 章）")
    print(f"練什麼：{material.trains}")
    print("─" * 56)
    for i, question in enumerate(questions, 1):
        print(f"{i}. {question.prompt}")
        if not args.no_answer:
            print(f"   答：{question.answer}")
            if question.hint:
                print(f"   提示：{question.hint}")
        print()
    print("★ 每次不超過 15 分鐘，時間到就停——即使他還想做（第 21 章）。")
    return 0


def _abc_store(cfg: settings_mod.Settings) -> behavior.AbcStore:
    return behavior.AbcStore(cfg.data_dir / "abc.jsonl")


def cmd_abc(args: argparse.Namespace, cfg: settings_mod.Settings) -> int:
    record = behavior.AbcRecord(
        date=parse_date(args.date),
        time=args.time,
        antecedent=args.a,
        behavior=args.b,
        consequence=args.c,
        duration_min=args.duration,
        setting=args.setting or "",
        hypothesis=args.function or "",
    )
    _abc_store(cfg).append(record)
    print(f"已記錄 ABC　{record.date} {record.time}")
    return 0


def cmd_function(args: argparse.Namespace, cfg: settings_mod.Settings) -> int:
    records = _abc_store(cfg).all()
    summary = behavior.summarize_functions(records)

    print(f"ABC 記錄　共 {summary.total} 筆")
    print("─" * 56)
    if not records:
        print("還沒有任何 ABC 記錄。第 35 章：連續兩週、至少 10 筆，一次只記一個行為。")
        return 0

    for key, label in behavior.FUNCTIONS.items():
        print(f"  {label:<14}{summary.counts.get(key, 0):>3} 筆")
    print("─" * 56)

    if not summary.enough_data:
        # 【WHY 不足就不給結論】低於門檻時給出的「功能」，反映的是最近一次事件的印象，
        # 而依印象選策略，正是第 35 章要避免的那件事。
        print(f"筆數不足（{summary.total} / {behavior.MIN_RECORDS_FOR_HYPOTHESIS}）。"
              f"先記滿，再談功能——不足時的結論只是最近一次事件的印象。")
        return 0

    if summary.top is None:
        print("每一筆都沒有填功能假設。回頭把 C 欄從頭讀一遍：他因此得到了什麼？")
        return 0

    print(f"目前最可能的功能：{summary.top_label}")
    latest = records[-1]
    print("\n假設句（可直接貼進 IEP）：")
    print(f"  {behavior.hypothesis_sentence(latest.antecedent, latest.behavior, summary.top)}")

    do, dont = behavior.strategy_for(summary.top)
    print("\n該做：")
    for item in do:
        print(f"  ✓ {item}")
    print("不該做：")
    for item in dont:
        print(f"  ✗ {item}")
    print("\n★ 假設要驗證：改一項前事或後果，觀察兩週。完全沒動 = 功能可能猜錯了。")
    return 0


def cmd_assets(args: argparse.Namespace, cfg: settings_mod.Settings) -> int:
    profile = _load_profile(cfg)
    out_dir = Path(args.out or cfg.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    assets = [
        visuals.checklist_card(args.tasks or ["擦黑板", "排桌椅", "倒垃圾"],
                               role=profile.role_title),
        visuals.token_board(count=args.tokens, topic=profile.fixation_topic),
        visuals.price_cards([("區間車", 150), ("自強號", 400),
                             ("便當", 100), ("門票", 800)]),
        visuals.timetable_card([("13:00", "區間車"), ("13:30", "自強號"),
                                ("14:00", "普悠瑪")]),
        visuals.task_analysis_card(args.steps or [
            "拿起毛巾放在桌上", "攤平，四角展開", "左邊對齊右邊", "壓平中線",
            "下緣對齊上緣", "壓平", "放進籃子（同一方向）",
        ]),
        # 記錄表：這幾張是每天要填的，一張紙一個月，貼冰箱
        visuals.daily_log(),
        visuals.abc_form(),
        visuals.sleep_log(),
        visuals.preference_form(),
    ]
    for asset in assets:
        (out_dir / asset.filename).write_text(asset.content, encoding="utf-8")
        print(f"已產生 {out_dir / asset.filename}")
    print("用瀏覽器開啟後直接列印（選「符合頁面」），護貝後即可使用。")
    return 0


def cmd_redflags(args: argparse.Namespace, cfg: settings_mod.Settings) -> int:
    print("紅旗清單（出現任一項，當天就醫）")
    print("─" * 56)
    for flag in safety.RED_FLAGS:
        print(f"□ {flag.text}　→ {flag.action}")
    print("─" * 56)
    print("永遠不要：")
    for item in safety.NEVER_DO:
        print(f"· {item}")
    return 0


def cmd_stages(args: argparse.Namespace, cfg: settings_mod.Settings) -> int:
    for stage in stages.all_stages():
        print(f"{stage.code}　{stage.name}（{stage.school_phase}・主核心 {stage.main_core}）")
        for criterion in stage.criteria:
            print(f"    · {criterion.label}：{criterion.target_text()}")
    return 0


def cmd_materials(args: argparse.Namespace, cfg: settings_mod.Settings) -> int:
    for material in curriculum.all_materials():
        drill = "有題庫" if material.has_drill else "流程（無題庫）"
        print(f"{material.code}　{material.name}　"
              f"[{curriculum.DIMENSIONS[material.dimension]}]　"
              f"第 {material.chapter} 章　{drill}")
        print(f"      練什麼：{material.trains}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="railway",
        description="《慢車到站》教材與追蹤工具包（純標準庫，零依賴）",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="建立個案設定（不含可識別資訊）")
    p_init.add_argument("--code", help="代號，例如 J")
    p_init.add_argument("--stage", default="S1", help="目前站別 S1..S6")
    p_init.add_argument("--topic", help="固著主題，例如 火車")
    p_init.add_argument("--role", help="角色稱號，例如 維修長")
    p_init.add_argument("--chain-level", type=int, default=1, dest="chain_level")
    p_init.set_defaults(func=cmd_init)

    p_rec = sub.add_parser("record", help="記錄一天（不超過三分鐘）")
    p_rec.add_argument("--date", required=True, help="YYYY-MM-DD")
    p_rec.add_argument("--recovery", type=int, help="情緒回復時間（秒）")
    p_rec.add_argument("--tasks", help="交辦總數/獨立完成數，例如 5/2")
    p_rec.add_argument("--chain", type=int, help="當日穩定完成的指令步數")
    p_rec.add_argument("--fixation", type=int, help="固著話題總時長（分）")
    p_rec.add_argument("--structured", action="store_true", default=None,
                       help="該次固著敘述達到「有結構」")
    p_rec.add_argument("--sleep", type=float, help="睡眠時數")
    p_rec.add_argument("--note", help="備註（例如：昨晚很晚睡）")
    p_rec.set_defaults(func=cmd_record)

    p_report = sub.add_parser("report", help="產生週報與趨勢")
    p_report.add_argument("--days", type=int, default=14)
    p_report.set_defaults(func=cmd_report)

    p_gate = sub.add_parser("gate", help="離站判定（三道門）")
    p_gate.add_argument("stage", help="S1..S6")
    p_gate.add_argument("--days", type=int, default=14)
    p_gate.add_argument("--set", action="append", metavar="指標=數值",
                        help="人工觀察的指標值，可重複")
    p_gate.add_argument("--foundation", action="append", metavar="紅燈事由",
                        help="地基門的紅燈，可重複；有任何一項即未通過")
    p_gate.add_argument("--caregiver-flags", type=int, default=0, dest="caregiver_flags",
                        help="照顧者自檢勾選項目數（≥3 未通過）")
    p_gate.set_defaults(func=cmd_gate)

    p_drill = sub.add_parser("drill", help="產生教材題目")
    p_drill.add_argument("material", help="M01..M09")
    p_drill.add_argument("--count", type=int, default=5)
    p_drill.add_argument("--seed", type=int)
    p_drill.add_argument("--no-answer", action="store_true", help="列印給孩子的版本")
    p_drill.set_defaults(func=cmd_drill)

    p_abc = sub.add_parser("abc", help="記錄一筆 ABC（第 35 章）")
    p_abc.add_argument("--date", required=True, help="YYYY-MM-DD")
    p_abc.add_argument("--time", required=True, help="HH:MM")
    p_abc.add_argument("-a", required=True, metavar="前事",
                       help="之前發生了什麼、誰在場、剛被要求什麼")
    p_abc.add_argument("-b", required=True, metavar="行為", help="他實際做了什麼")
    p_abc.add_argument("-c", required=True, metavar="後果",
                       help="★ 他因此得到了什麼（不是你做了什麼）")
    p_abc.add_argument("--duration", type=int, help="持續分鐘")
    p_abc.add_argument("--setting", help="家／學校／社區／機構")
    p_abc.add_argument("--function", choices=sorted(behavior.FUNCTIONS),
                       help="功能假設：attention / escape / tangible / sensory")
    p_abc.set_defaults(func=cmd_abc)

    sub.add_parser("function", help="統計行為功能並給出策略建議").set_defaults(func=cmd_function)

    p_assets = sub.add_parser("assets", help="產生列印用 SVG")
    p_assets.add_argument("--out", help="輸出目錄")
    p_assets.add_argument("--tasks", nargs="*", help="檢核卡的任務（最多 5 項）")
    p_assets.add_argument("--tokens", type=int, default=3)
    p_assets.add_argument("--steps", nargs="*", help="工作分析的步驟（最多 12 步）")
    p_assets.set_defaults(func=cmd_assets)

    sub.add_parser("redflags", help="顯示紅旗清單").set_defaults(func=cmd_redflags)
    sub.add_parser("stages", help="顯示六站與離站標準").set_defaults(func=cmd_stages)
    sub.add_parser("materials", help="顯示十組教材").set_defaults(func=cmd_materials)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    cfg = settings_mod.load()
    try:
        result: int = args.func(args, cfg)
        return result
    except (ValidationError, ValueError, KeyError) as exc:
        print(f"錯誤：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
