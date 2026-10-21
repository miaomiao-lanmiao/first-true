from __future__ import annotations

import asyncio
import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from .ai.prompts import PROVIDER_REGISTRY, SYSTEM_PROMPTS
from .ai.provider import create_provider
from .config import CONFIG_DIR, get_provider_config, load_config, save_config
from .storage import safe_child, write_private

STATIC_DIR = Path(__file__).parent / "web_static"
BASE_DIR = CONFIG_DIR
SESSION_DIR = BASE_DIR / "sessions"
SKILLS_DIR = BASE_DIR / "skills"
MCP_FILE = BASE_DIR / "mcp.json"
TASKS_FILE = BASE_DIR / "tasks.json"
AVATAR_FILE = BASE_DIR / "avatar.txt"

app = FastAPI(title="Echo Web")


@app.middleware("http")
async def local_requests_only(request: Request, call_next):
    host = request.url.hostname
    if host not in ("127.0.0.1", "localhost", "::1"):
        return JSONResponse({"detail": "Loopback host required."}, status_code=400)
    origin = request.headers.get("origin")
    if origin and request.url.path.startswith("/api/"):
        expected = f"{request.url.scheme}://{request.headers.get('host', '')}"
        if origin != expected:
            return JSONResponse({"detail": "Same-origin API requests required."}, status_code=403)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


# ===================== Models =====================
class ChatRequest(BaseModel):
    messages: list[dict[str, str]]
    session_id: Optional[str] = None


class ConfigRequest(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    tts_enabled: Optional[bool] = None
    tts_engine: Optional[str] = None
    tts_endpoint: Optional[str] = None
    tts_api_key: Optional[str] = None
    tts_voice: Optional[str] = None
    tts_rate: Optional[float] = None
    stt_engine: Optional[str] = None
    stt_endpoint: Optional[str] = None
    stt_api_key: Optional[str] = None
    stt_lang: Optional[str] = None
    avatar: Optional[str] = None


class SessionRequest(BaseModel):
    title: str = "新会话"


class MessagesRequest(BaseModel):
    messages: list[dict[str, str]]


class SkillRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    enabled: Optional[bool] = None


class McpRequest(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    token: Optional[str] = None
    enabled: Optional[bool] = None


# ===================== Helpers =====================
def _providers_payload() -> list[dict[str, Any]]:
    return [
        {"id": k, "name": c["name"], "models": c["models"], "needs_key": c.get("needs_key", True)}
        for k, c in PROVIDER_REGISTRY.items()
    ]


def _mask_key(key: str) -> str:
    if not key:
        return ""
    return "[REDACTED]"


# ---- sessions ----
def _session_path(sid: str) -> Path:
    try:
        return safe_child(SESSION_DIR, sid, ".json")
    except ValueError as error:
        raise HTTPException(400, "Invalid session identifier.") from error


def _skill_path(sid: str) -> Path:
    try:
        return safe_child(SKILLS_DIR, sid)
    except ValueError as error:
        raise HTTPException(400, "Invalid skill identifier.") from error


def _load_session(sid: str) -> Optional[dict]:
    p = _session_path(sid)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _save_session(data: dict):
    write_private(_session_path(data["id"]), json.dumps(data, ensure_ascii=False, indent=2))


# ---- skills (SKILL.md with YAML frontmatter) ----
def _slug(name: str) -> str:
    s = re.sub(r"[^\w一-龥-]+", "-", name.lower()).strip("-")[:80]
    return s or "skill"


def _parse_skill(md_path: Path) -> dict:
    text = md_path.read_text(encoding="utf-8")
    meta = {"name": md_path.parent.name, "description": "", "enabled": True}
    content = text
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.DOTALL)
    if m:
        fm, content = m.group(1), m.group(2)
        for line in fm.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k == "name":
                    meta["name"] = v
                elif k == "description":
                    meta["description"] = v
                elif k == "enabled":
                    meta["enabled"] = v.lower() in ("true", "1", "yes", "on")
    return {"id": md_path.parent.name, "name": meta["name"], "description": meta["description"], "enabled": meta["enabled"], "content": content.strip()}


def _write_skill(sid_dir: Path, name: str, description: str, content: str, enabled: bool):
    sid_dir.mkdir(parents=True, exist_ok=True)
    fm = f"---\nname: {name}\ndescription: {description}\nenabled: {str(enabled).lower()}\n---\n\n{content}\n"
    write_private(sid_dir / "SKILL.md", fm)


def _list_skills() -> list[dict]:
    out = []
    if not SKILLS_DIR.exists():
        return out
    for d in SKILLS_DIR.iterdir():
        if not d.is_symlink() and d.is_dir() and (d / "SKILL.md").is_file():
            out.append(_parse_skill(d / "SKILL.md"))
    return out


def _enabled_skills_block() -> str:
    skills = [s for s in _list_skills() if s.get("enabled")]
    if not skills:
        return ""
    parts = ["\n\n# 可用技能 (Skills)", "以下是当前启用的技能，根据用户需求适时选用："]
    for s in skills:
        parts.append(f"\n## {s['name']}\n{s['description']}\n{s['content']}")
    return "\n".join(parts)


# ---- mcp ----
def _load_mcp() -> list[dict]:
    if not MCP_FILE.exists():
        return []
    return json.loads(MCP_FILE.read_text(encoding="utf-8"))


def _save_mcp(data: list[dict]):
    write_private(MCP_FILE, json.dumps(data, ensure_ascii=False, indent=2))


def _public_mcp(entry: dict) -> dict:
    return {**{key: value for key, value in entry.items() if key != "token"}, "token_set": bool(entry.get("token"))}


# ===================== API =====================
@app.get("/api/providers")
def api_providers():
    return JSONResponse(_providers_payload())


@app.get("/api/config")
def api_get_config():
    cfg = load_config()
    ai = cfg.get("ai", {})
    provider_id = ai.get("provider")
    models = []
    for k, c in PROVIDER_REGISTRY.items():
        if k == provider_id:
            models = c.get("models", [])
            break
    return JSONResponse({
        "provider": provider_id,
        "model": ai.get("model"),
        "models": models,
        "api_key_masked": _mask_key(ai.get("api_key", "")),
        "api_key_set": bool(ai.get("api_key")),
        "providers": _providers_payload(),
        "tts_enabled": bool(ai.get("tts_enabled", False)),
        "tts_engine": ai.get("tts_engine", "browser"),
        "tts_endpoint": ai.get("tts_endpoint", ""),
        "tts_api_key_set": bool(ai.get("tts_api_key")),
        "tts_voice": ai.get("tts_voice", ""),
        "tts_rate": ai.get("tts_rate", 1.0),
        "stt_engine": ai.get("stt_engine", "browser"),
        "stt_endpoint": ai.get("stt_endpoint", ""),
        "stt_api_key_set": bool(ai.get("stt_api_key")),
        "stt_lang": ai.get("stt_lang", "zh-CN"),
        "avatar": ai.get("avatar", ""),
    })


@app.post("/api/config")
def api_set_config(req: ConfigRequest):
    cfg = load_config()
    ai = cfg.setdefault("ai", {})
    if req.provider is not None:
        ai["provider"] = req.provider
    if req.model is not None:
        ai["model"] = req.model
    if req.api_key is not None:
        if req.api_key == "" or req.api_key.lower() == "clear":
            ai.pop("api_key", None)
        else:
            ai["api_key"] = req.api_key
    if req.tts_enabled is not None:
        ai["tts_enabled"] = req.tts_enabled
    if req.tts_engine is not None:
        ai["tts_engine"] = req.tts_engine
    if req.tts_endpoint is not None:
        ai["tts_endpoint"] = req.tts_endpoint
    if req.tts_api_key is not None:
        ai["tts_api_key"] = "" if req.tts_api_key.lower() == "clear" else req.tts_api_key
    if req.tts_voice is not None:
        ai["tts_voice"] = req.tts_voice
    if req.tts_rate is not None:
        ai["tts_rate"] = req.tts_rate
    if req.stt_engine is not None:
        ai["stt_engine"] = req.stt_engine
    if req.stt_endpoint is not None:
        ai["stt_endpoint"] = req.stt_endpoint
    if req.stt_api_key is not None:
        ai["stt_api_key"] = "" if req.stt_api_key.lower() == "clear" else req.stt_api_key
    if req.stt_lang is not None:
        ai["stt_lang"] = req.stt_lang
    if req.avatar is not None:
        ai["avatar"] = req.avatar
        write_private(AVATAR_FILE, req.avatar)
    save_config(cfg)
    return JSONResponse({"ok": True, "status": "saved"})


@app.post("/api/chat")
async def api_chat(req: ChatRequest):
    cfg = load_config()
    provider_config = get_provider_config(cfg)
    provider = create_provider(provider_config)

    messages = req.messages[:]
    if not any(m.get("role") == "system" for m in messages):
        system = SYSTEM_PROMPTS["default"] + _enabled_skills_block()
        messages.insert(0, {"role": "system", "content": system})

    full = ""

    async def event_stream():
        nonlocal full
        try:
            async for chunk in provider.chat_stream(messages):
                full += chunk
                yield f"data: {json.dumps({'token': chunk}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"
        except Exception:
            yield f"data: {json.dumps({'error': 'Provider request failed. Check configuration and connectivity.'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ---- sessions ----
@app.get("/api/sessions")
def api_list_sessions():
    out = []
    for p in SESSION_DIR.glob("*.json"):
        if p.is_symlink():
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        out.append({"id": d["id"], "title": d.get("title", "会话"),
                    "updated_at": d.get("updated_at", ""), "count": len(d.get("messages", []))})
    out.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return JSONResponse(out)


@app.post("/api/sessions")
def api_create_session(req: SessionRequest):
    sid = uuid.uuid4().hex[:12]
    now = datetime.now().isoformat()
    data = {"id": sid, "title": req.title, "messages": [], "created_at": now, "updated_at": now}
    _save_session(data)
    return JSONResponse(data)


@app.get("/api/sessions/{sid}")
def api_get_session(sid: str):
    d = _load_session(sid)
    if not d:
        raise HTTPException(404, "session not found")
    return JSONResponse({"id": d["id"], "title": d.get("title", ""), "messages": d.get("messages", [])})


@app.delete("/api/sessions/{sid}")
def api_delete_session(sid: str):
    p = _session_path(sid)
    if p.exists():
        p.unlink()
    return JSONResponse({"ok": True})


@app.put("/api/sessions/{sid}/messages")
def api_update_messages(sid: str, req: MessagesRequest):
    d = _load_session(sid)
    if not d:
        raise HTTPException(404, "session not found")
    d["messages"] = req.messages
    d["updated_at"] = datetime.now().isoformat()
    if req.messages and d.get("title") in (None, "", "新会话"):
        d["title"] = req.messages[0]["content"][:30]
    _save_session(d)
    return JSONResponse({"ok": True})


# ---- skills ----
@app.get("/api/skills")
def api_list_skills():
    return JSONResponse(_list_skills())


@app.post("/api/skills")
def api_create_skill(req: SkillRequest):
    if not req.name:
        raise HTTPException(400, "Skill name is required.")
    sid = _slug(req.name) + "-" + uuid.uuid4().hex[:4]
    directory = _skill_path(sid)
    _write_skill(directory, req.name, req.description or "", req.content or "", True)
    return JSONResponse(_parse_skill(directory / "SKILL.md"))


@app.put("/api/skills/{sid}")
def api_update_skill(sid: str, req: SkillRequest):
    d = _skill_path(sid)
    if not (d / "SKILL.md").exists():
        raise HTTPException(404, "skill not found")
    cur = _parse_skill(d / "SKILL.md")
    _write_skill(d, req.name or cur["name"], req.description or cur["description"],
                 req.content if req.content is not None else cur["content"],
                 req.enabled if req.enabled is not None else cur["enabled"])
    return JSONResponse(_parse_skill(d / "SKILL.md"))


@app.delete("/api/skills/{sid}")
def api_delete_skill(sid: str):
    d = _skill_path(sid)
    if d.exists():
        import shutil
        shutil.rmtree(d)
    return JSONResponse({"ok": True})


# ---- mcp ----
@app.get("/api/mcp")
def api_list_mcp():
    return JSONResponse([_public_mcp(entry) for entry in _load_mcp()])


@app.post("/api/mcp")
def api_create_mcp(req: McpRequest):
    data = _load_mcp()
    entry = {"id": uuid.uuid4().hex[:12], "name": req.name, "url": req.url,
             "token": req.token, "enabled": req.enabled}
    data.append(entry)
    _save_mcp(data)
    return JSONResponse(_public_mcp(entry))


@app.put("/api/mcp/{mid}")
def api_update_mcp(mid: str, req: McpRequest):
    data = _load_mcp()
    for e in data:
        if e["id"] == mid:
            if req.name is not None: e["name"] = req.name
            if req.url is not None: e["url"] = req.url
            if req.token is not None: e["token"] = "" if req.token.lower() == "clear" else req.token
            if req.enabled is not None: e["enabled"] = req.enabled
            _save_mcp(data)
            return JSONResponse(_public_mcp(e))
    raise HTTPException(404, "mcp not found")


@app.delete("/api/mcp/{mid}")
def api_delete_mcp(mid: str):
    data = _load_mcp()
    data = [e for e in data if e["id"] != mid]
    _save_mcp(data)
    return JSONResponse({"ok": True})


# ---- scheduled tasks ----
def _load_tasks() -> list[dict]:
    if TASKS_FILE.exists():
        try:
            return json.loads(TASKS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_tasks(data: list[dict]):
    write_private(TASKS_FILE, json.dumps(data, ensure_ascii=False, indent=2))


def _task_due(t: dict, now: datetime) -> bool:
    last = t.get("last_run")
    last_dt = datetime.fromisoformat(last) if last else None
    if t.get("mode") == "daily":
        hh, mm = (t.get("time") or "09:00").split(":")
        target = now.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
        if now < target:
            return False
        if last_dt is None:
            return True
        return last_dt.date() < now.date()
    # interval (minutes)
    iv = max(1, int(t.get("interval") or 60))
    if last_dt is None:
        return True
    return (now - last_dt).total_seconds() >= iv * 60


async def _generate(messages: list[dict]) -> str:
    cfg = load_config()
    provider = create_provider(get_provider_config(cfg))
    out = []
    async for chunk in provider.chat_stream(messages):
        out.append(chunk)
    return "".join(out)


async def _run_task(t: dict, now: datetime | None = None):
    now = now or datetime.now()
    history = t.get("history") or []
    session_id = t.get("session_id")
    result = ""
    ok = True
    try:
        system = SYSTEM_PROMPTS["default"] + _enabled_skills_block()
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": t["prompt"]},
        ]
        result = await _generate(messages)
        # persist into a dedicated session
        if not session_id or not _session_path(session_id).exists():
            session_id = uuid.uuid4().hex[:12]
            t["session_id"] = session_id
            _save_session({"id": session_id, "title": "⏰ " + t["name"], "messages": [], "created_at": now.isoformat()})
        s = _load_session(session_id)
        s.setdefault("messages", []).append({"role": "user", "content": t["prompt"]})
        s["messages"].append({"role": "assistant", "content": result})
        s["updated_at"] = now.isoformat()
        _save_session(s)
    except Exception:
        ok = False
        result = "运行失败：请检查服务配置和网络连接。"
    t["last_run"] = now.isoformat()
    preview = result[:160].replace("\n", " ")
    history.insert(0, {"ts": now.isoformat(), "ok": ok, "preview": preview, "len": len(result)})
    t["history"] = history[:25]
    return result


async def _scheduler_loop():
    while True:
        try:
            for t in _load_tasks():
                if t.get("enabled") and _task_due(t, datetime.now()):
                    await _run_task(t)
                    tasks = _load_tasks()
                    for i, x in enumerate(tasks):
                        if x["id"] == t["id"]:
                            tasks[i] = t
                    _save_tasks(tasks)
        except Exception:
            print("[scheduler] Task failed; check configuration and connectivity.")
        await asyncio.sleep(20)


@app.on_event("startup")
def _start_scheduler():
    try:
        asyncio.get_running_loop().create_task(_scheduler_loop())
    except Exception:
        pass


class TaskRequest(BaseModel):
    name: Optional[str] = None
    prompt: Optional[str] = None
    mode: Optional[str] = None
    interval: Optional[int] = None
    time: Optional[str] = None
    enabled: Optional[bool] = None


@app.get("/api/tasks")
def api_list_tasks():
    return JSONResponse(_load_tasks())


@app.post("/api/tasks")
def api_create_task(req: TaskRequest):
    if not req.name or not req.prompt:
        raise HTTPException(400, "name 和 prompt 必填")
    t = {
        "id": uuid.uuid4().hex[:10],
        "name": req.name,
        "prompt": req.prompt,
        "mode": req.mode or "interval",
        "interval": req.interval or 60,
        "time": req.time or "09:00",
        "enabled": True if req.enabled is None else req.enabled,
        "last_run": None,
        "history": [],
        "session_id": None,
    }
    data = _load_tasks()
    data.append(t)
    _save_tasks(data)
    return JSONResponse(t)


@app.put("/api/tasks/{tid}")
def api_update_task(tid: str, req: TaskRequest):
    data = _load_tasks()
    for t in data:
        if t["id"] == tid:
            for k in ("name", "prompt", "mode", "interval", "time", "enabled"):
                v = getattr(req, k)
                if v is not None:
                    t[k] = v
            _save_tasks(data)
            return JSONResponse(t)
    raise HTTPException(404, "task not found")


@app.delete("/api/tasks/{tid}")
def api_delete_task(tid: str):
    data = [t for t in _load_tasks() if t["id"] != tid]
    _save_tasks(data)
    return JSONResponse({"ok": True})


@app.post("/api/tasks/{tid}/run")
async def api_run_task(tid: str):
    data = _load_tasks()
    for t in data:
        if t["id"] == tid:
            await _run_task(t)
            for i, x in enumerate(data):
                if x["id"] == tid:
                    data[i] = t
            _save_tasks(data)
            return JSONResponse(t)
    raise HTTPException(404, "task not found")


# ---- static ----
@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/{path:path}")
def static_files(path: str):
    target = (STATIC_DIR / path).resolve()
    if STATIC_DIR in target.parents or target == STATIC_DIR:
        if target.is_file():
            return FileResponse(target)
    return FileResponse(STATIC_DIR / "index.html")
