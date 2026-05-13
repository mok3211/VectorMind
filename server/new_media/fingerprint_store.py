from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(slots=True, frozen=True)
class FingerprintRecord:
    account_id: int
    platform: str
    profile_dir: Path
    state_file: Path
    updated_at: datetime
    extra: dict[str, Any]

    def to_json(self) -> str:
        payload = {
            "account_id": self.account_id,
            "platform": self.platform,
            "profile_dir": str(self.profile_dir),
            "state_file": str(self.state_file),
            "updated_at": self.updated_at.isoformat(),
            "extra": self.extra,
        }
        return json.dumps(payload, ensure_ascii=False)


class FingerprintStore:
    """
    账号指纹/会话状态持久化：
    - profile_dir: 持久化浏览器上下文目录（cookies/local storage/指纹环境）
    - state_file: playwright storage_state 备份
    """

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def resolve(self, *, platform: str, account_id: int) -> tuple[Path, Path]:
        base = (self.root_dir / platform / str(account_id)).resolve()
        profile_dir = (base / "profile").resolve()
        state_file = (base / "state.json").resolve()
        profile_dir.mkdir(parents=True, exist_ok=True)
        state_file.parent.mkdir(parents=True, exist_ok=True)
        return profile_dir, state_file

    def create_record(
        self,
        *,
        platform: str,
        account_id: int,
        extra: dict[str, Any] | None = None,
    ) -> FingerprintRecord:
        profile_dir, state_file = self.resolve(platform=platform, account_id=account_id)
        return FingerprintRecord(
            account_id=account_id,
            platform=platform,
            profile_dir=profile_dir,
            state_file=state_file,
            updated_at=datetime.utcnow(),
            extra=extra or {},
        )
