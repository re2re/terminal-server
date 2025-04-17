from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from send_to_telegram import forward_ticket
import os

app = FastAPI()

# Serve static files under /static
app.mount("/static", StaticFiles(directory="static"), name="static")

# Root route serves index.html
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

# TODO: Implement these API endpoints:
# GET  /api/terminals
# POST /api/terminals/add
# POST /api/terminals/toggle
# POST /api/terminals/delete
