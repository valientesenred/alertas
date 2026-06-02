import secrets
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from ..models import Usuaria, ContactoConfianza, Ubicacion, EstadoUsuaria
from ..config import settings
from . import whatsapp
from .alertas import activar_alerta

PASOS = {
    "inicio":      "inicio",
    "nombre":      "esperando_nombre",
    "clave":       "esperando_clave",
    "contactos":   "esperando_contactos",
    "listo":       "listo",
}

async def procesar_mensaje(db: AsyncSession, numero: str, texto: str, tipo: str = "text", lat: float = None, lon: float = None):
    texto = texto.strip()
    res = await db.execute(select(Usuaria).where(Usuaria.numero_whatsapp == numero))
    usuaria: Usuaria | None = res.scalar_one_or_none()

    # ── NUEVA USUARIA ────────────────────────────────────────────────────────
    if not usuaria:
        if texto.upper() in ["HOLA", "INICIO", "REGISTRAR", "AYUDA", "START"]:
            usuaria = Usuaria(numero_whatsapp=numero, estado=EstadoUsuaria.pendiente)
            db.add(usuaria)
            await db.flush()
            await whatsapp.enviar_mensaje(numero,
                "Hola. Soy tu asistente de seguridad personal.\n\n"
                "Voy a ayudarte a configurar tu red de apoyo en caso de emergencia.\n\n"
                "Este proceso toma solo 3 minutos. Asegurate de estar en un lugar tranquilo.\n\n"
                "Para comenzar, cuéntame: ¿Cuál es tu nombre?"
            )
        else:
            await whatsapp.enviar_mensaje(numero, "Escribe HOLA para comenzar tu registro de seguridad.")
        return

    estado = usuaria.estado

    # ── ALERTA ACTIVA (cualquier mensaje puede ser la clave) ─────────────────
    if estado == EstadoUsuaria.activa and usuaria.palabra_clave:
        if texto.upper() == usuaria.palabra_clave.upper():
            usuaria.estado = EstadoUsuaria.en_alerta
            ub_res = await db.execute(
                select(Ubicacion)
                .where(Ubicacion.usuaria_id == usuaria.id)
                .order_by(Ubicacion.created_at.desc())
                .limit(1)
            )
            ultima_ub = ub_res.scalar_one_or_none()
            await activar_alerta(db, usuaria, ultima_ub)
            return

    # ── FLUJO DE ONBOARDING ──────────────────────────────────────────────────
    if estado == EstadoUsuaria.pendiente:
        # Esperando nombre
        if not usuaria.nombre:
            usuaria.nombre = texto.title()
            await db.flush()
            token = secrets.token_urlsafe(32)
            usuaria.token_ubicacion = token
            url_pwa = f"{settings.BASE_URL}/alertas/ubicacion/{token}"
            await whatsapp.enviar_mensaje(numero,
                f"Gracias, {usuaria.nombre}.\n\n"
                f"Ahora necesito configurar tu ubicacion para saber a que CAI reportar en caso de emergencia.\n\n"
                f"Por favor abre este enlace y acepta el permiso de ubicacion:\n{url_pwa}\n\n"
                f"Cuando termines, escribe LISTO."
            )
            return

        # Esperando confirmacion de ubicacion
        if texto.upper() == "LISTO":
            ub_res = await db.execute(
                select(func.count()).where(Ubicacion.usuaria_id == usuaria.id)
            )
            tiene_ubicacion = ub_res.scalar() > 0
            if not tiene_ubicacion:
                await whatsapp.enviar_mensaje(numero,
                    "Aún no recibo tu ubicacion. Por favor abre el enlace anterior y acepta el permiso."
                )
                return
            await whatsapp.enviar_mensaje(numero,
                "Ubicacion registrada.\n\n"
                "Ahora agrega hasta 5 contactos de confianza.\n"
                "Envialos en este formato:\n\n"
                "Nombre | Número | Relacion\n\n"
                "Ejemplo:\n"
                "Maria Lopez | 3001234567 | mamá\n\n"
                "Cuando termines con todos, escribe FIN."
            )
            return

        # Recibiendo contactos
        if texto.upper() == "FIN":
            ct_res = await db.execute(
                select(func.count()).where(ContactoConfianza.usuaria_id == usuaria.id)
            )
            n = ct_res.scalar()
            if n == 0:
                await whatsapp.enviar_mensaje(numero, "Aun no tienes contactos. Agrega al menos uno.")
                return
            # Pedir palabra clave
            await whatsapp.enviar_mensaje(numero,
                f"Tienes {n} contacto(s) registrado(s).\n\n"
                "Ultimo paso: elige tu palabra clave de emergencia.\n"
                "Puede ser algo que parezca normal, por ejemplo:\n"
                "ya llegué / donde estás / llámame\n\n"
                "Escribe la frase que usarás."
            )
            return

        if "|" in texto:
            partes = [p.strip() for p in texto.split("|")]
            if len(partes) >= 2:
                ct_res = await db.execute(
                    select(func.count()).where(ContactoConfianza.usuaria_id == usuaria.id)
                )
                n = ct_res.scalar()
                if n >= 5:
                    await whatsapp.enviar_mensaje(numero, "Ya tienes 5 contactos, que es el maximo. Escribe FIN para continuar.")
                    return
                contacto = ContactoConfianza(
                    usuaria_id=usuaria.id,
                    nombre=partes[0],
                    numero_whatsapp=partes[1].replace(" ", "").replace("-", ""),
                    relacion=partes[2] if len(partes) > 2 else None,
                    orden=n + 1,
                )
                db.add(contacto)
                await db.flush()
                await whatsapp.enviar_mensaje(numero,
                    f"Contacto {n+1} registrado: {contacto.nombre}.\n"
                    f"Agrega otro o escribe FIN para terminar."
                )
            return

        # Recibir palabra clave
        ct_res = await db.execute(
            select(func.count()).where(ContactoConfianza.usuaria_id == usuaria.id)
        )
        if ct_res.scalar() > 0 and not usuaria.palabra_clave and len(texto) >= 3:
            usuaria.palabra_clave = texto
            usuaria.estado = EstadoUsuaria.activa
            await db.flush()
            await whatsapp.enviar_mensaje(numero,
                f"Todo listo, {usuaria.nombre}.\n\n"
                f"Tu red de seguridad esta configurada.\n"
                f"Palabra clave: \"{texto}\"\n\n"
                "Cuando la envies aqui, alertaremos a tus contactos y al CAI mas cercano.\n\n"
                "Recuerda: puedes actualizar tu ubicacion en cualquier momento escribiendo UBICACION."
            )
            return

    # ── COMANDOS GLOBALES ────────────────────────────────────────────────────
    if texto.upper() == "UBICACION":
        token = secrets.token_urlsafe(32)
        usuaria.token_ubicacion = token
        await db.flush()
        url_pwa = f"{settings.BASE_URL}/alertas/ubicacion/{token}"
        await whatsapp.enviar_mensaje(numero,
            f"Actualiza tu ubicacion aqui:\n{url_pwa}"
        )
