import os
import json
import threading
from fastapi import FastAPI, HTTPException, Depends, status, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from send_to_telegram import forward_ticket

TERMINALS_FILE = "terminals.json"
_lock = threading.Lock()
connections = {}

app = FastAPI()

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=FileResponse)
async def root():
    return FileResponse(os.path.join("static", "index.html"))

def load_terminals():
    if not os.path.exists(TERMINALS_FILE):
        return []
    with open(TERMINALS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_terminals(terms):
    with _lock:
        with open(TERMINALS_FILE, "w", encoding="utf-8") as f:
            json.dump(terms, f, ensure_ascii=False, indent=2)

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
        raise HTTPException(400, "id, login и password обязательны")
    terms = load_terminals()
    if any(t["id"] == term_id for t in terms):
        raise HTTPException(400, "Терминал с таким id уже существует")
    terms.append({"id": term_id, "login": login, "password": password, "enabled": True, "total": 0})
    save_terminals(terms)
    return JSONResponse({"status": "ok"})

@app.post("/api/terminals/toggle")
async def toggle_terminal(payload: dict):
    term_id = payload.get("id")
    if term_id is None:
        raise HTTPException(400, "id обязательны")
    terms = load_terminals()
    for t in terms:
        if t["id"] == term_id:
            t["enabled"] = not t.get("enabled", False)
            save_terminals(terms)
            return JSONResponse({"status": "ok", "enabled": t["enabled"]})
    raise HTTPException(404, "Терминал не найден")

@app.post("/api/terminals/delete")
async def delete_terminal(payload: dict):
    term_id = payload.get("id")
    if term_id is None:
        raise HTTPException(400, "id обязательны")
    terms = load_terminals()
    new_terms = [t for t in terms if t["id"] != term_id]
    if len(new_terms) == len(terms):
        raise HTTPException(404, "Терминал не найден")
    save_terminals(new_terms)
    return JSONResponse({"status": "ok"})

@app.post("/api/terminals/auth")
async def auth_terminal(payload: dict):
    print(f"[AUTH_REQ] payload: {payload!r}")
    term_id = payload.get("id")
    login = payload.get("login")
    password = payload.get("password")
    if not (term_id and login and password):
        print("[AUTH_REQ] missing fields")
        raise HTTPException(400, "id, login и password обязательны")
    terms = load_terminals()
    for t in terms:
        if t["id"] == term_id:
            if t["login"] == login and t["password"] == password:
                print(f"[AUTH_OK] terminal {term_id}")
                return JSONResponse({"status": "ok", "id": term_id})
            else:
                print(f"[AUTH_FAIL] bad credentials for {term_id}")
                raise HTTPException(401, "Неверный логин или пароль")
    print(f"[AUTH_FAIL] terminal {term_id} not found")
    raise HTTPException(404, "Терминал не найден")

security = HTTPBasic()
VALID_USERNAME = os.getenv("API_LOGIN", "demo_user")
VALID_PASSWORD = os.getenv("API_PASSWORD", "demo_pass")

def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.username != VALID_USERNAME or credentials.password != VALID_PASSWORD:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Неверный логин или пароль",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

@app.post("/api/tickets")
async def receive_ticket(ticket: dict, username: str = Depends(authenticate)):
    print(f"[TICKET] от {username}: {ticket}")
    await forward_ticket(ticket)
    term_id = ticket.get("terminal_id")
    amount = ticket.get("amount", 0)
    terms = load_terminals()
    updated = False
    for t in terms:
        if t["id"] == term_id:
            t["total"] = t.get("total", 0) + amount
            updated = True
            break
    if updated:
        save_terminals(terms)
    else:
        print(f"⚠ Терминал {term_id} не найден")
    return JSONResponse({"status": "forwarded", "total_updated": updated})

@app.websocket("/ws/{term_id}")
async def websocket_endpoint(websocket: WebSocket, term_id: str):
    await websocket.accept()
    connections[term_id] = websocket
    print(f"[WS_CONNECTED] {term_id}")
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
                print(f"[WS_PING] {term_id}")
    except WebSocketDisconnect:
        print(f"[WS_DISCONNECTED] {term_id}")
        connections.pop(term_id, None)
