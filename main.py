from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from send_to_telegram import forward_ticket
import os

app = FastAPI()
app.mount("/", StaticFiles(directory="static", html=True), name="static")
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