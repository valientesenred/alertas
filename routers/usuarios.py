from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..database import get_db
from ..models import Usuaria, Ubicacion, ContactoConfianza
from ..schemas import UsuariaOut, ContactoCreate, ContactoOut, UbicacionCreate, TokenUbicacionOut
from ..config import settings
import secrets

router = APIRouter(prefix="/usuarias", tags=["usuarias"])

# ── Mini web: página de captura de ubicación ──────────────────────────────────

MINIWEB_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Configuración de seguridad</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: system-ui, sans-serif; background: #f8f9fa; display: flex;
            align-items: center; justify-content: center; min-height: 100vh; padding: 1rem; }}
    .card {{ background: white; border-radius: 16px; padding: 2rem; max-width: 400px;
             width: 100%; box-shadow: 0 4px 20px rgba(0,0,0,.08); text-align: center; }}
    .icon {{ font-size: 3rem; margin-bottom: 1rem; }}
    h1 {{ color: #6b21a8; font-size: 1.25rem; margin-bottom: .75rem; }}
    p {{ color: #555; font-size: .95rem; line-height: 1.5; margin-bottom: 1.5rem; }}
    button {{ background: #7c3aed; color: white; border: none; border-radius: 10px;
              padding: .85rem 2rem; font-size: 1rem; cursor: pointer; width: 100%; }}
    button:disabled {{ background: #a78bfa; cursor: not-allowed; }}
    .estado {{ margin-top: 1rem; font-size: .9rem; color: #555; min-height: 2rem; }}
    .ok {{ color: #16a34a; font-weight: 600; }}
    .err {{ color: #dc2626; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">🛡️</div>
    <h1>Red de seguridad personal</h1>
    <p>Necesitamos tu ubicación para poder alertar al CAI más cercano si la necesitas.<br>
       Tu ubicación solo se usa en emergencias.</p>
    <button id="btn" onclick="capturar()">Permitir ubicación</button>
    <p class="estado" id="estado"></p>
  </div>
  <script>
    async function capturar() {{
      const btn = document.getElementById('btn');
      const est = document.getElementById('estado');
      btn.disabled = true;
      est.textContent = 'Obteniendo ubicación...';
      if (!navigator.geolocation) {{
        est.textContent = 'Tu navegador no soporta geolocalización.';
        est.className = 'estado err'; btn.disabled = false; return;
      }}
      navigator.geolocation.getCurrentPosition(async pos => {{
        est.textContent = 'Enviando...';
        const r = await fetch('/alertas/ubicacion/{token}/guardar', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{
            latitud: pos.coords.latitude,
            longitud: pos.coords.longitude,
            precision_metros: pos.coords.accuracy,
            fuente: 'pwa'
          }})
        }});
        if (r.ok) {{
          est.textContent = '✅ Ubicación guardada correctamente. Puedes cerrar esta página y volver a WhatsApp.';
          est.className = 'estado ok'; btn.style.display = 'none';
        }} else {{
          est.textContent = 'Error al guardar. Intenta de nuevo.';
          est.className = 'estado err'; btn.disabled = false;
        }}
      }}, () => {{
        est.textContent = 'Permiso denegado. Por favor activa la ubicación en tu navegador.';
        est.className = 'estado err'; btn.disabled = false;
      }});
    }}
  </script>
</body>
</html>"""

@router.get("/ubicacion/{token}", response_class=HTMLResponse, include_in_schema=False)
async def pagina_ubicacion(token: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Usuaria).where(Usuaria.token_ubicacion == token))
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Token inválido")
    return MINIWEB_HTML.replace("{token}", token)

@router.post("/ubicacion/{token}/guardar")
async def guardar_ubicacion_pwa(token: str, datos: UbicacionCreate, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Usuaria).where(Usuaria.token_ubicacion == token))
    usuaria = res.scalar_one_or_none()
    if not usuaria:
        raise HTTPException(status_code=404, detail="Token inválido")
    ub = Ubicacion(usuaria_id=usuaria.id, **datos.model_dump())
    db.add(ub)
    return {"ok": True}

# ── Contactos ─────────────────────────────────────────────────────────────────

@router.get("/{usuaria_id}/contactos", response_model=list[ContactoOut])
async def listar_contactos(usuaria_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(ContactoConfianza).where(ContactoConfianza.usuaria_id == usuaria_id)
        .order_by(ContactoConfianza.orden)
    )
    return res.scalars().all()

@router.post("/{usuaria_id}/contactos", response_model=ContactoOut)
async def agregar_contacto(usuaria_id: str, datos: ContactoCreate, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import func
    n = (await db.execute(
        select(func.count()).where(ContactoConfianza.usuaria_id == usuaria_id)
    )).scalar()
    if n >= 5:
        raise HTTPException(status_code=400, detail="Máximo 5 contactos")
    c = ContactoConfianza(usuaria_id=usuaria_id, **datos.model_dump())
    db.add(c)
    await db.flush()
    return c

@router.delete("/{usuaria_id}/contactos/{contacto_id}", status_code=204)
async def eliminar_contacto(usuaria_id: str, contacto_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(ContactoConfianza).where(
            ContactoConfianza.id == contacto_id,
            ContactoConfianza.usuaria_id == usuaria_id
        )
    )
    c = res.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404)
    await db.delete(c)
