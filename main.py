from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from send_to_telegram import forward_ticket
import os
import json
import threading

app = FastAPI()

# Serve static files under /static
app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static",
)

# Root route serves index.html
@app.get("/", response_class=FileResponse)
async def root():
    return FileResponse(os.path.join("static", "index.html"))

# File and lock for terminals storage
tERMINALS_FILE = "terminals.json"
nTERMINALS_LOCK = threading.Lock()

def load_terminals():
    if not os.path.exists(TERMINALS_FILE):
        return []
    with open(TERMINALS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_terminals(terminals):
    with TERMINALS_LOCK:
        with open(TERMINALS_FILE, "w", encoding="utf-8") as f:
            json.dump(terminals, f, indent=2, ensure_ascii=False)

# API endpoints for terminals
@app.get("/api/terminals")
async def get_terminals():
    return load_terminals()

@app.post("/api/terminals/add")
async def add_terminal(data: dict):
    term_id = data.get("id")
    login = data.get("login")
    password = data.get("password")
    if not term_id or not login or not password:
        raise HTTPException(status_code=400, detail="Необходимо указать id, login и password")
    terminals = load_terminals()
    if any(t["id"] == term_id for t in terminals):
        raise HTTPException(status_code=400, detail="Терминал с таким ID уже существует")
    terminals.append({
        "id": term_id,
        "login": login,
        "password": password,
        "enabled": True,
        "total": 0
    })
    save_terminals(terminals)
    return {"status": "ok"}

@app.post("/api/terminals/toggle")
async def toggle_terminal(data: dict):
    term_id = data.get("id")
    terminals = load_terminals()
    for t in terminals:
        if t.get("id") == term_id:
            t["enabled"] = not t.get("enabled", False)
            save_terminals(terminals)
            return {"status": "ok", "enabled": t["enabled"]}
    raise HTTPException(status_code=404, detail="Терминал не найден")

@app.post("/api/terminals/delete")
async def delete_terminal(data: dict):
    term_id = data.get("id")
    terminals = load_terminals()
    new_terms = [t for t in terminals if t.get("id") != term_id]
    if len(new_terms) == len(terminals):
        raise HTTPException(status_code=404, detail="Терминал не найден")
    save_terminals(new_terms)
    return {"status": "ok"}

# Existing ticket endpoint with authentication
security = HTTPBasic()
VALID_USERNAME = os.getenv("API_LOGIN", "demo_user")
VALID_PASSWORD = os.getenv("API_PASSWORD", "demo_pass")

def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.username != VALID_USERNAME or credentials.password != VALID_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

@app.post("/api/tickets")
async def receive_ticket(ticket: dict, username: str = Depends(authenticate)):
    print(f"[TICKET] Получен от {username}: {ticket}")
    await forward_ticket(ticket)
    return JSONResponse(content={"status": "forwarded to Telegram"})
