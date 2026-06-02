from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime
from .models import EstadoUsuaria, EstadoAlerta


# ── Usuaria ──────────────────────────────────────────────────────────────────

class UsuariaCreate(BaseModel):
    numero_whatsapp: str
    nombre: Optional[str] = None

class UsuariaUpdate(BaseModel):
    nombre: Optional[str] = None
    palabra_clave: Optional[str] = None

class UsuariaOut(BaseModel):
    id: str
    numero_whatsapp: str
    nombre: Optional[str]
    estado: EstadoUsuaria
    created_at: datetime
    total_contactos: Optional[int] = 0
    total_alertas: Optional[int] = 0

    class Config:
        from_attributes = True


# ── Contacto ─────────────────────────────────────────────────────────────────

class ContactoCreate(BaseModel):
    nombre: str
    numero_whatsapp: str
    relacion: Optional[str] = None
    orden: Optional[int] = 1

    @field_validator("orden")
    @classmethod
    def orden_valido(cls, v):
        if v < 1 or v > 5:
            raise ValueError("El orden debe estar entre 1 y 5")
        return v

class ContactoOut(BaseModel):
    id: str
    nombre: str
    numero_whatsapp: str
    relacion: Optional[str]
    activo: bool
    orden: int

    class Config:
        from_attributes = True


# ── Ubicación ─────────────────────────────────────────────────────────────────

class UbicacionCreate(BaseModel):
    latitud: float
    longitud: float
    precision_metros: Optional[float] = None
    es_tiempo_real: bool = False
    fuente: str = "pwa"

class UbicacionOut(BaseModel):
    id: str
    latitud: float
    longitud: float
    precision_metros: Optional[float]
    es_tiempo_real: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Alerta ────────────────────────────────────────────────────────────────────

class AlertaOut(BaseModel):
    id: str
    usuaria_id: str
    estado: EstadoAlerta
    contactos_notificados: int
    cai_nombre: Optional[str]
    cai_telefono: Optional[str]
    cai_distancia_km: Optional[float]
    created_at: datetime
    ubicacion: Optional[UbicacionOut] = None

    class Config:
        from_attributes = True

class AlertaUpdate(BaseModel):
    estado: Optional[EstadoAlerta] = None
    notas_admin: Optional[str] = None


# ── Admin ─────────────────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_usuarias: int
    usuarias_activas: int
    alertas_hoy: int
    alertas_mes: int
    alertas_atendidas: int


# ── Token ubicación (mini web) ────────────────────────────────────────────────

class TokenUbicacionOut(BaseModel):
    token: str
    url: str
