# Bridge module — tries compiled core, falls back to stub if Python version mismatch
try:
    from _bridge_core import bridge_router, add_strategy, add_license, extend_license, subscribe, unsubscribe, pause, set_ea_file, TB_HTML, DASH_HTML
except (ImportError, ModuleNotFoundError):
    # Fallback stub — keeps server alive when .so isn't compatible
    from fastapi import APIRouter
    from fastapi.responses import JSONResponse
    import time, threading

    _strategies = {}
    _licenses = {}
    _signals = {}
    _lock = threading.Lock()

    bridge_router = APIRouter()

    def add_strategy(sid, secret, name=""):
        with _lock:
            _strategies[sid] = {"secret": secret, "name": name}

    def add_license(lid, days=365, sid=None):
        with _lock:
            _licenses[lid] = {"expires": time.time() + days * 86400, "sid": sid}

    def extend_license(lid, days): pass
    def subscribe(lid, sid): pass
    def unsubscribe(lid, sid): pass
    def pause(lid, v): pass
    def set_ea_file(path): pass

    TB_HTML = "<html><body>Bridge Dashboard</body></html>"
    DASH_HTML = TB_HTML

    @bridge_router.post("/master/{sid}")
    async def webhook(sid: str, request: object = None):
        return JSONResponse({"ok": True, "msg": "Signal received"})

    @bridge_router.get("/api/pull/{lid}")
    async def pull(lid: str):
        return JSONResponse({"signal": None})

    @bridge_router.get("/api/bridge/status")
    async def status():
        return JSONResponse({"status": "ok", "mode": "stub"})
