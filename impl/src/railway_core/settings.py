"""設定:全部來自環境變數,全部有預設值。

【WHY 不做設定檔】
多一個設定檔,就多一個「家長不知道要改哪裡」的地方。這個工具的所有
設定加起來只有五項,而且每一項都有能直接用的預設值——沒有設定檔,
就沒有人會卡在設定檔上。

【WHY 沒有「姓名」設定】
見 schemas.Profile:可識別資訊留在附錄D 的私人檔,工具鏈不碰。
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# 【注意】新增環境變數時,必須同步更新 .env.example——
# scripts/check_assets.py 會比對這兩者,漏掉會讓 CI 失敗。
ENV_DATA_DIR = "RAILWAY_DATA_DIR"
ENV_OUT_DIR = "RAILWAY_OUT_DIR"
ENV_PROFILE_CODE = "RAILWAY_PROFILE_CODE"
ENV_ROLE_TITLE = "RAILWAY_ROLE_TITLE"
ENV_FIXATION_TOPIC = "RAILWAY_FIXATION_TOPIC"

ENV_VARS: tuple[str, ...] = (
    ENV_DATA_DIR, ENV_OUT_DIR, ENV_PROFILE_CODE, ENV_ROLE_TITLE, ENV_FIXATION_TOPIC,
)


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    out_dir: Path
    profile_code: str
    role_title: str
    fixation_topic: str

    @property
    def records_path(self) -> Path:
        return self.data_dir / "records.jsonl"

    @property
    def profile_path(self) -> Path:
        return self.data_dir / "profile.json"


def load() -> Settings:
    return Settings(
        data_dir=Path(os.environ.get(ENV_DATA_DIR, "data")),
        out_dir=Path(os.environ.get(ENV_OUT_DIR, "out")),
        profile_code=os.environ.get(ENV_PROFILE_CODE, "J"),
        role_title=os.environ.get(ENV_ROLE_TITLE, "維修長"),
        fixation_topic=os.environ.get(ENV_FIXATION_TOPIC, "火車"),
    )
