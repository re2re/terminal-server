from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from send_to_telegram import forward_ticket
import os

app = FastAPI()

# 1) Статика по URL /static
app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static",
)

# 2) Корневой маршрут отдает index.html
@app.get("/", response_class=FileResponse)
async def root():
    return FileResponse(os.path.join("static", "index.html"))

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

# NOTE: Реализуйте, если еще нет, следующие эндпоинты:
# GET  /api/terminals         — вернуть список терминалов
# POST /api/terminals/add     — добавить терминал: {id, login, password}
# POST /api/terminals/toggle  — вкл/выкл терминал: {id}
# POST /api/terminals/delete  — удалить терминал: {id}

