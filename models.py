from sqlalchemy import (
    Column, String, Boolean, DateTime, Float,
    Integer, ForeignKey, Text, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from database import Base


def gen_uuid():
    return str(uuid.uuid4())


class EstadoUsuaria(str, enum.Enum):
    pendiente    = "pendiente"
    activa       = "activa"
    inactiva     = "inactiva"
    en_alerta    = "en_alerta"


class EstadoAlerta(str, enum.Enum):
    activada     = "activada"
    atendida     = "atendida"
    falsa_alarma = "falsa_alarma"
    cancelada    = "cancelada"


class Usuaria(Base):
    __tablename__ = "usuarias"

    id               = Column(String, primary_key=True, default=gen_uuid)
    numero_whatsapp  = Column(String(20), unique=True, nullable=False, index=True)
    nombre           = Column(String(120), nullable=True)
    palabra_clave    = Column(String(50), nullable=True)
    estado           = Column(SAEnum(EstadoUsuaria), default=EstadoUsuaria.pendiente, nullable=False)
    token_ubicacion  = Column(String(64), nullable=True, unique=True)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    updated_at       = Column(DateTime(timezone=True), onupdate=func.now())

    # Relaciones
    contactos        = relationship("ContactoConfianza", back_populates="usuaria", cascade="all, delete-orphan")
    ubicaciones      = relationship("Ubicacion", back_populates="usuaria", cascade="all, delete-orphan")
    alertas          = relationship("Alerta", back_populates="usuaria", cascade="all, delete-orphan")


class ContactoConfianza(Base):
    __tablename__ = "contactos_confianza"

    id              = Column(String, primary_key=True, default=gen_uuid)
    usuaria_id      = Column(String, ForeignKey("usuarias.id"), nullable=False)
    nombre          = Column(String(120), nullable=False)
    numero_whatsapp = Column(String(20), nullable=False)
    relacion        = Column(String(60), nullable=True)   # mamá, amiga, vecina…
    activo          = Column(Boolean, default=True)
    orden           = Column(Integer, default=1)          # 1-5
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    usuaria         = relationship("Usuaria", back_populates="contactos")


class Ubicacion(Base):
    __tablename__ = "ubicaciones"

    id              = Column(String, primary_key=True, default=gen_uuid)
    usuaria_id      = Column(String, ForeignKey("usuarias.id"), nullable=False)
    latitud         = Column(Float, nullable=False)
    longitud        = Column(Float, nullable=False)
    precision_metros= Column(Float, nullable=True)
    es_tiempo_real  = Column(Boolean, default=False)
    fuente          = Column(String(20), default="pwa")  # pwa | whatsapp
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    usuaria         = relationship("Usuaria", back_populates="ubicaciones")


class Alerta(Base):
    __tablename__ = "alertas"

    id                   = Column(String, primary_key=True, default=gen_uuid)
    usuaria_id           = Column(String, ForeignKey("usuarias.id"), nullable=False)
    ubicacion_id         = Column(String, ForeignKey("ubicaciones.id"), nullable=True)
    estado               = Column(SAEnum(EstadoAlerta), default=EstadoAlerta.activada)
    palabra_usada        = Column(String(50), nullable=True)
    contactos_notificados= Column(Integer, default=0)
    cai_nombre           = Column(String(200), nullable=True)
    cai_telefono         = Column(String(20), nullable=True)
    cai_distancia_km     = Column(Float, nullable=True)
    notas_admin          = Column(Text, nullable=True)
    created_at           = Column(DateTime(timezone=True), server_default=func.now())
    updated_at           = Column(DateTime(timezone=True), onupdate=func.now())

    usuaria              = relationship("Usuaria", back_populates="alertas")
    ubicacion            = relationship("Ubicacion")
