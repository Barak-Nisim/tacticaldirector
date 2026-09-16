"""Caches AI narratives so re-submitting an identical encounter doesn't
re-spend tokens on a response that would come back identical.

Keyed by a hash of the exact payload the narrator sends to the model
(`prompts.build_payload`: the character, the enemy list and their threat
tiers, the terrain flags, the round number, and every ranked action's
score/tier/category reasons). That payload is the whole of what determines
the narration, so there's no separate TTL to reason about -- any real
change to the encounter or to what the scoring engine made of it is itself
a cache miss.

One file per distinct encounter, at ~/.tacticaldirector/narrative_cache/
by default, outside the repo -- overridable via
TACTICALDIRECTOR_NARRATIVE_CACHE_DIR, which the test suite uses so tests
never touch a real user's home directory (mirrors play/session.py's
storage pattern).
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from tacticaldirector.ai.prompts import build_payload
from tacticaldirector.models import TacticalResult


def _cache_dir() -> Path:
    override = os.environ.get("TACTICALDIRECTOR_NARRATIVE_CACHE_DIR")
    base = Path(override) if override else Path.home() / ".tacticaldirector" / "narrative_cache"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _input_key(result: TacticalResult) -> str:
    blob = json.dumps(build_payload(result), sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _cache_path(input_key: str) -> Path:
    return _cache_dir() / f"{input_key}.json"


def get_cached_narrative(result: TacticalResult) -> dict | None:
    input_key = _input_key(result)
    path = _cache_path(input_key)
    if not path.exists():
        return None
    cached = json.loads(path.read_text(encoding="utf-8"))
    if cached.get("input_key") != input_key:
        return None
    return cached["narrative"]


def store_narrative(result: TacticalResult, narrative: dict) -> None:
    input_key = _input_key(result)
    payload = {"input_key": input_key, "narrative": narrative}
    _cache_path(input_key).write_text(json.dumps(payload, indent=2), encoding="utf-8")
