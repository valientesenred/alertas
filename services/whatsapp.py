import httpx
from config import settings

WA_BASE = f"https://graph.facebook.com/{settings.WA_API_VERSION}/{settings.WA_PHONE_NUMBER_ID}"

async def enviar_mensaje(numero: str, texto: str) -> bool:
    url = f"{WA_BASE}/messages"
    headers = {
        "Authorization": f"Bearer {settings.WA_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": texto},
    }
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, json=payload, headers=headers)
        return r.status_code == 200

async def enviar_mensaje_template(numero: str, template: str, params: list) -> bool:
    url = f"{WA_BASE}/messages"
    headers = {
        "Authorization": f"Bearer {settings.WA_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "template",
        "template": {
            "name": template,
            "language": {"code": "es"},
            "components": [{"type": "body", "parameters": params}],
        },
    }
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, json=payload, headers=headers)
        return r.status_code == 200
