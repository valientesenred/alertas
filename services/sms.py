"""
Servicio de envío de SMS via Twilio.
Se activa solo cuando SMS_ENABLED=True y las credenciales están configuradas.
"""
import logging
from config import settings

logger = logging.getLogger(__name__)


def _get_client():
    """Retorna cliente Twilio si está configurado, None si no."""
    if not settings.SMS_ENABLED:
        return None
    if not all([settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN, settings.TWILIO_PHONE_NUMBER]):
        logger.warning("SMS_ENABLED=True pero faltan credenciales de Twilio.")
        return None
    try:
        from twilio.rest import Client
        return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    except ImportError:
        logger.error("Paquete 'twilio' no instalado. Agrega twilio>=9.0.0 a requirements.txt")
        return None


def _formatear_numero(numero: str) -> str:
    """
    Convierte número colombiano al formato E.164 para Twilio.
    Ejemplos:
        3001234567      → +573001234567
        573001234567    → +573001234567
        +573001234567   → +573001234567
    """
    numero = numero.strip().replace(" ", "").replace("-", "")
    if numero.startswith("+"):
        return numero
    if numero.startswith("57"):
        return f"+{numero}"
    if len(numero) == 10 and numero.startswith("3"):
        return f"+57{numero}"
    # Para otros países — retornar con + por defecto
    return f"+{numero}"


async def enviar_sms(numero: str, mensaje: str) -> bool:
    """
    Envía un SMS al número indicado.
    Retorna True si se envió correctamente, False en caso contrario.
    El fallo de SMS nunca debe interrumpir el flujo de alertas.
    """
    client = _get_client()
    if not client:
        logger.info("SMS desactivado o sin configurar — se omite envío a %s", numero)
        return False

    numero_e164 = _formatear_numero(numero)

    try:
        message = client.messages.create(
            body=mensaje,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=numero_e164,
        )
        logger.info("SMS enviado a %s — SID: %s", numero_e164, message.sid)
        return True
    except Exception as exc:
        logger.error("Error enviando SMS a %s: %s", numero_e164, exc)
        return False


async def enviar_sms_alerta(numero: str, nombre_usuaria: str, maps_link: str,
                             cai_nombre: str | None, hora: str) -> bool:
    """
    Envía el SMS de alerta de emergencia con formato compacto (160 caracteres max).
    """
    if cai_nombre:
        mensaje = (
            f"ALERTA EMERGENCIA\n"
            f"{nombre_usuaria} puede estar en peligro.\n"
            f"Ubicacion: {maps_link}\n"
            f"CAI cercano: {cai_nombre}\n"
            f"Hora: {hora}\n"
            f"Llama al 123."
        )
    else:
        mensaje = (
            f"ALERTA EMERGENCIA\n"
            f"{nombre_usuaria} puede estar en peligro.\n"
            f"Ubicacion: {maps_link}\n"
            f"Hora: {hora}\n"
            f"Llama al 123."
        )

    return await enviar_sms(numero, mensaje)
