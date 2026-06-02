from fastapi import APIRouter, Request, Response, Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from config import settings
from database import get_db
from models import Usuaria, Ubicacion
from services.bot import procesar_mensaje
from sqlalchemy import select

router = APIRouter(prefix="/webhook", tags=["webhook"])

@router.get("")
async def verificar_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_challenge: str = Query(alias="hub.challenge"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
):
    if hub_mode == "subscribe" and hub_verify_token == settings.WA_VERIFY_TOKEN:
        return Response(content=hub_challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Token inválido")

@router.post("")
async def recibir_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        data = await request.json()
        entry = data["entry"][0]["changes"][0]["value"]
        messages = entry.get("messages", [])
        for msg in messages:
            numero = msg["from"]
            tipo = msg["type"]
            texto = ""
            lat, lon = None, None

            if tipo == "text":
                texto = msg["text"]["body"]
            elif tipo == "location":
                lat = msg["location"]["latitude"]
                lon = msg["location"]["longitude"]
                texto = "__location__"

                # Guardar ubicación recibida desde WhatsApp
                res = await db.execute(select(Usuaria).where(Usuaria.numero_whatsapp == numero))
                usuaria = res.scalar_one_or_none()
                if usuaria:
                    ub = Ubicacion(
                        usuaria_id=usuaria.id,
                        latitud=lat, longitud=lon,
                        fuente="whatsapp",
                        es_tiempo_real="live_period" in msg.get("location", {}),
                    )
                    db.add(ub)
                    await db.flush()

            await procesar_mensaje(db, numero, texto, tipo, lat, lon)
    except Exception:
        pass
    return {"status": "ok"}
