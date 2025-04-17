import os
import json
import threading
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from send_to_telegram import forward_ticket

# --- Константы и блокировка для безопасной записи ---
TERMINALS_FILE = "terminals.json"
_lock = threading.Lock()

app = FastAPI()

# --- Статика ---
# все файлы из static/ доступны по /static/...
app.mount("/static", StaticFiles(directory="static"), name="static")

# корень отдаёт наш frontend
@app.get("/", response_class=FileResponse)
async def root():
    return FileResponse(os.path.join("static", "index.html"))

# --- Хелперы для работы с terminals.json ---
def load_terminals():
    if not os.path.exists(TERMINALS_FILE):
        return []
    with open(TERMINALS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_terminals(terms):
    with _lock:
        with open(TERMINALS_FILE, "w", encoding="utf-8") as f:
            json.dump(terms, f, ensure_ascii=False, indent=2)

# --- Эндпоинты для терминалов ---

@app.get("/api/terminals")
async def get_terminals():
    terms = load_terminals()
    return [
        {"id": t["id"], "enabled": t.get("enabled", False), "total": t.get("total", 0)}
        for t in terms
    ]

@app.post("/api/terminals/add")
async def add_terminal(payload: dict):
    term_id = payload.get("id")
    login = payload.get("login")
    password = payload.get("password")
    if not (term_id and login and password):
        raise HTTPException(status_code=400, detail="id, login и password обязательны")
    terms = load_terminals()
    if any(t["id"] == term_id for t in terms):
        raise HTTPException(status_code=400, detail="Терминал с таким id уже существует")
    new_term = {
        "id": term_id,
        "login": login,
        "password": password,
        "enabled": True,
        "total": 0
    }
    terms.append(new_term)
    save_terminals(terms)
    return JSONResponse(content={"status": "ok"})

@app.post("/api/terminals/toggle")
async def toggle_terminal(payload: dict):
    term_id = payload.get("id")
    if term_id is None:
        raise HTTPException(status_code=400, detail="id обязательны")
    terms = load_terminals()
    for t in terms:
        if t["id"] == term_id:
            t["enabled"] = not t.get("enabled", False)
            save_terminals(terms)
            return JSONResponse(content={"status": "ok", "enabled": t["enabled"]})
    raise HTTPException(status_code=404, detail="Терминал не найден")

@app.post("/api/terminals/delete")
async def delete_terminal(payload: dict):
    term_id = payload.get("id")
    if term_id is None:
        raise HTTPException(status_code=400, detail="id обязательны")
    terms = load_terminals()
    new_terms = [t for t in terms if t["id"] != term_id]
    if len(new_terms) == len(terms):
        raise HTTPException(status_code=404, detail="Терминал не найден")
    save_terminals(new_terms)
    return JSONResponse(content={"status": "ok"})

# --- Эндпоинт тикетов с HTTP Basic авторизацией ---

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