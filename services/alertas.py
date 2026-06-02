import math
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models import Usuaria, Alerta, Ubicacion, EstadoAlerta, ContactoConfianza
from . import whatsapp

# CAIs de Cali con coordenadas (fuente: Datos Abiertos / Secretaría de Seguridad)
CAIS_CALI = [
    {"nombre": "CAI Aguablanca",        "telefono": "318-861-1522", "lat": 3.3865, "lon": -76.4976},
    {"nombre": "CAI Andrés Sanín",      "telefono": "318-861-1522", "lat": 3.4516, "lon": -76.5320},
    {"nombre": "CAI Caldas",            "telefono": "318-861-1522", "lat": 3.3960, "lon": -76.5217},
    {"nombre": "CAI El Calvario",       "telefono": "318-861-1522", "lat": 3.4517, "lon": -76.5326},
    {"nombre": "CAI Ciudad Jardín",     "telefono": "318-861-1522", "lat": 3.3700, "lon": -76.5410},
    {"nombre": "CAI Siloe",             "telefono": "318-861-1522", "lat": 3.4367, "lon": -76.5596},
    {"nombre": "CAI El Guabal",         "telefono": "318-861-1522", "lat": 3.4113, "lon": -76.5302},
    {"nombre": "CAI Limonar",           "telefono": "318-861-1522", "lat": 3.3724, "lon": -76.5252},
    {"nombre": "CAI Salomia",           "telefono": "318-861-1522", "lat": 3.4856, "lon": -76.5091},
    {"nombre": "CAI San Fernando",      "telefono": "318-861-1522", "lat": 3.3951, "lon": -76.5365},
    {"nombre": "CAI Terrón Colorado",   "telefono": "318-861-1522", "lat": 3.4657, "lon": -76.5558},
    {"nombre": "CAI Villanueva",        "telefono": "318-861-1522", "lat": 3.4411, "lon": -76.5131},
    {"nombre": "Patrulla Púrpura MECAL","telefono": "318-861-1522", "lat": 3.4516, "lon": -76.5320},
]

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def cai_mas_cercano(lat: float, lon: float) -> dict:
    return min(CAIS_CALI, key=lambda c: haversine(lat, lon, c["lat"], c["lon"]))

def link_maps(lat: float, lon: float) -> str:
    return f"https://maps.google.com/?q={lat},{lon}"

async def activar_alerta(db: AsyncSession, usuaria: Usuaria, ubicacion: Ubicacion | None) -> Alerta:
    cai = None
    if ubicacion:
        cai = cai_mas_cercano(ubicacion.latitud, ubicacion.longitud)

    alerta = Alerta(
        usuaria_id=usuaria.id,
        ubicacion_id=ubicacion.id if ubicacion else None,
        estado=EstadoAlerta.activada,
        palabra_usada=usuaria.palabra_clave,
        cai_nombre=cai["nombre"] if cai else None,
        cai_telefono=cai["telefono"] if cai else None,
        cai_distancia_km=round(haversine(ubicacion.latitud, ubicacion.longitud, cai["lat"], cai["lon"]), 2) if (cai and ubicacion) else None,
    )
    db.add(alerta)
    await db.flush()

    contactos_result = await db.execute(
        select(ContactoConfianza).where(
            ContactoConfianza.usuaria_id == usuaria.id,
            ContactoConfianza.activo == True
        ).order_by(ContactoConfianza.orden)
    )
    contactos = contactos_result.scalars().all()

    hora = datetime.now().strftime("%d/%m/%Y %H:%M")
    maps_link = link_maps(ubicacion.latitud, ubicacion.longitud) if ubicacion else "Ubicación no disponible"
    nombre_usuaria = usuaria.nombre or "Una persona"

    msg_contacto = (
        f"ALERTA DE SEGURIDAD\n\n"
        f"{nombre_usuaria} puede estar en peligro.\n\n"
        f"Ubicacion: {maps_link}\n"
        f"Hora: {hora}\n\n"
    )
    if cai and ubicacion:
        msg_contacto += (
            f"CAI mas cercano: {cai['nombre']}\n"
            f"Tel: {cai['telefono']}\n"
            f"Distancia: {alerta.cai_distancia_km} km\n\n"
        )
    msg_contacto += "Por favor contactala o llama al 123."

    count = 0
    for c in contactos:
        ok = await whatsapp.enviar_mensaje(c.numero_whatsapp, msg_contacto)
        if ok:
            count += 1

    alerta.contactos_notificados = count
    await db.flush()
    return alerta
