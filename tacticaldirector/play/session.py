"""Persists Play Mode sessions between requests/CLI invocations.

Sessions live at ~/.tacticaldirector/sessions/<session_id>.json by default,
one file per session -- outside the repo entirely, mirroring
marketsignal/history.py's proven pattern exactly. The location is
overridable via TACTICALDIRECTOR_SESSION_DIR, which the test suite uses so
tests never touch a real user's home directory.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict
from pathlib import Path

from tacticaldirector.models import Character, Encounter, Enemy, PlaySession, RoundOutcome, Terrain


def _session_dir() -> Path:
    override = os.environ.get("TACTICALDIRECTOR_SESSION_DIR")
    base = Path(override) if override else Path.home() / ".tacticaldirector" / "sessions"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _session_path(session_id: str) -> Path:
    return _session_dir() / f"{session_id}.json"


def new_session_id() -> str:
    return uuid.uuid4().hex[:12]


def _encounter_from_dict(raw: dict) -> Encounter:
    return Encounter(
        character=Character(**raw["character"]),
        enemies=tuple(Enemy(**e) for e in raw["enemies"]),
        terrain=Terrain(**raw["terrain"]),
        round_number=raw["round_number"],
    )


def _session_from_dict(raw: dict) -> PlaySession:
    return PlaySession(
        session_id=raw["session_id"],
        scenario_id=raw["scenario_id"],
        seed=raw["seed"],
        encounter=_encounter_from_dict(raw["encounter"]),
        round_log=tuple(RoundOutcome(**r) for r in raw["round_log"]),
        status=raw["status"],
        narrate=raw.get("narrate", False),  # older session files predate this field
    )


def save_session(session: PlaySession) -> None:
    path = _session_path(session.session_id)
    path.write_text(json.dumps(asdict(session), indent=2), encoding="utf-8")


def load_session(session_id: str) -> PlaySession | None:
    path = _session_path(session_id)
    if not path.exists():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    return _session_from_dict(raw)


def start_session(
    scenario_id: str, encounter: Encounter, seed: int, narrate: bool = False
) -> PlaySession:
    session = PlaySession(
        session_id=new_session_id(),
        scenario_id=scenario_id,
        seed=seed,
        encounter=encounter,
        round_log=(),
        status="in_progress",
        narrate=narrate,
    )
    save_session(session)
    return session
