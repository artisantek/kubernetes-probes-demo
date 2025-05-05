from fastapi import FastAPI, Response
import os

app    = FastAPI()
frozen = False            # toggled by /freeze and /unfreeze

def _json(txt: str, code: int = 200):
    return Response(txt, status_code=code, media_type="application/json")

# ---------- probe endpoints ----------

@app.get("/ready")
def ready():
    """
    Readiness: 503 while frozen, 200 otherwise.
    """
    return _json('{"status":"ok"}') if not frozen else _json('{"status":"frozen"}', 503)

@app.get("/live")
def live():
    """
    Liveness: always 200 as long as the process is alive.
    """
    return _json('{"status":"alive"}')

# ---------- control endpoints ----------

@app.post("/freeze")
def freeze():
    global frozen
    frozen = True
    return _json('{"status":"frozen"}')

@app.post("/unfreeze")
def unfreeze():
    global frozen
    frozen = False
    return _json('{"status":"unfrozen"}')

@app.post("/crash")
def crash():
    """
    Exit immediately – kubelet will detect liveness failure and restart container.
    """
    os._exit(1)