"""FastAPI web UI for TacticalDirector.

Thin wrapper around the same loader/scoring/report modules the CLI uses --
no scoring or narration logic lives here. Run locally with
`tacticaldirector serve`.
"""

from __future__ import annotations

import os
import random
from dataclasses import replace
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from tacticaldirector.loader import dump_encounter, load_encounter
from tacticaldirector.models import ARCHETYPES, Character, Encounter, Enemy, Terrain
from tacticaldirector.play.resolution import resolve_round
from tacticaldirector.play.scenarios import list_scenarios, scenario_path
from tacticaldirector.play.session import load_session, save_session, start_session
from tacticaldirector.scoring import score_encounter

WEB_DIR = Path(__file__).parent
SAMPLE_ENCOUNTER_PATH = WEB_DIR.parent.parent / "examples" / "sample_encounter.yaml"

app = FastAPI(title="TacticalDirector")
templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")


def _sample_encounter() -> Encounter:
    if SAMPLE_ENCOUNTER_PATH.exists():
        return load_encounter(SAMPLE_ENCOUNTER_PATH)
    return Encounter(
        character=Character(
            name="",
            archetype="warrior",
            level=1,
            hp_current=10,
            hp_max=10,
            resources_current=0,
            resources_max=0,
        ),
        enemies=(),
        terrain=Terrain(),
    )


def _ai_available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


@app.get("/", response_class=HTMLResponse)
def landing(request: Request):
    return templates.TemplateResponse(request, "landing.html", {})


@app.get("/how-it-works", response_class=HTMLResponse)
def how_it_works(request: Request):
    return templates.TemplateResponse(request, "how_it_works.html", {})


@app.get("/app", response_class=HTMLResponse)
def app_form(request: Request):
    encounter = _sample_encounter()
    return templates.TemplateResponse(
        request,
        "app_form.html",
        {
            "character": encounter.character,
            "enemies": encounter.enemies,
            "terrain": encounter.terrain,
            "round_number": encounter.round_number,
            "archetypes": sorted(ARCHETYPES),
            "ai_available": _ai_available(),
            "error": None,
        },
    )


@app.post("/advise", response_class=HTMLResponse)
async def advise(
    request: Request,
    name: str = Form(""),
    archetype: str = Form("warrior"),
    level: int = Form(1),
    hp_current: int = Form(0),
    hp_max: int = Form(1),
    resources_current: int = Form(0),
    resources_max: int = Form(0),
    round_number: int = Form(1),
    high_ground: str | None = Form(None),
    cover: str | None = Form(None),
    hazard: str | None = Form(None),
    use_ai: str | None = Form(None),
):
    form = await request.form()

    character = Character(
        name=name or "Unnamed",
        archetype=archetype.lower() if archetype.lower() in ARCHETYPES else "warrior",
        level=level,
        hp_current=hp_current,
        hp_max=max(hp_max, 1),
        resources_current=resources_current,
        resources_max=resources_max,
    )

    enemies = []
    for i in range(5):
        enemy_name = str(form.get(f"enemy_name_{i}") or "").strip()
        if not enemy_name:
            continue
        threat_tier = int(form.get(f"enemy_threat_{i}") or 1)
        enemies.append(Enemy(name=enemy_name, threat_tier=threat_tier))

    terrain = Terrain(
        high_ground=bool(high_ground),
        cover=bool(cover),
        hazard=bool(hazard),
    )

    encounter = Encounter(
        character=character,
        enemies=tuple(enemies),
        terrain=terrain,
        round_number=round_number,
    )

    result = score_encounter(encounter)
    encounter_yaml = dump_encounter(encounter)

    ai_narrative = None
    if use_ai and _ai_available():
        from tacticaldirector.ai.narrator import generate_narrative

        ai_narrative = generate_narrative(result)

    return templates.TemplateResponse(
        request,
        "report.html",
        {
            "result": result,
            "ai_narrative": ai_narrative,
            "encounter_yaml": encounter_yaml,
        },
    )


@app.get("/play", response_class=HTMLResponse)
def play_scenarios(request: Request):
    return templates.TemplateResponse(
        request, "play_scenarios.html", {"scenarios": list_scenarios()}
    )


@app.post("/play/start")
def play_start(scenario: str = Form(...), seed: str | None = Form(None)):
    encounter = load_encounter(scenario_path(scenario))
    seed_value = int(seed) if seed else random.SystemRandom().randrange(1_000_000)
    session = start_session(scenario, encounter, seed_value)
    return RedirectResponse(url=f"/play/{session.session_id}", status_code=303)


@app.get("/play/{session_id}", response_class=HTMLResponse)
def play_round(request: Request, session_id: str):
    session = load_session(session_id)
    if session is None:
        return templates.TemplateResponse(
            request,
            "play_round.html",
            {"session": None, "error": "Session not found. It may have expired."},
            status_code=404,
        )

    result = score_encounter(session.encounter) if session.status == "in_progress" else None
    last_outcome = session.round_log[-1] if session.round_log else None

    return templates.TemplateResponse(
        request,
        "play_round.html",
        {
            "session": session,
            "result": result,
            "last_outcome": last_outcome,
            "error": None,
        },
    )


@app.post("/play/{session_id}/act")
def play_act(session_id: str, action: str = Form(...)):
    session = load_session(session_id)
    if session is not None and session.status == "in_progress":
        rng = random.Random(session.seed + len(session.round_log))
        new_encounter, outcome, status = resolve_round(session.encounter, action, rng)
        updated = replace(
            session,
            encounter=new_encounter,
            round_log=session.round_log + (outcome,),
            status=status,
        )
        save_session(updated)

    return RedirectResponse(url=f"/play/{session_id}", status_code=303)
