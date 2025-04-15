import aiohttp
import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8112467398:AAGSQ9Vtkm3-jrtPV2MmPAaBahC7v0LknvU")
CHAT_ID = os.getenv("CHAT_ID", "-100")

async def forward_ticket(ticket: dict):
    msg = (
        "🎟️ *Новый тикет от терминала*\n"
        f"*Терминал:* `{ticket.get('terminal_number', '???')}`\n"
        f"*ID:* `{ticket.get('id', '---')}`\n"
        f"*Сумма:* `{ticket.get('amount', 0)} ₽`\n"
        f"*Время:* `{ticket.get('timestamp', '')}`"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=data) as resp:
            print(f"[TELEGRAM] status: {resp.status}")