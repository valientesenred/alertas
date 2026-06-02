from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, Date
from datetime import date, timedelta
from database import get_db
from models import Usuaria, Alerta, EstadoUsuaria, EstadoAlerta
from schemas import AlertaOut, AlertaUpdate, DashboardStats, UsuariaOut

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/stats", response_model=DashboardStats)
async def estadisticas(db: AsyncSession = Depends(get_db)):
    total = (await db.execute(select(func.count()).select_from(Usuaria))).scalar()
    activas = (await db.execute(
        select(func.count()).where(Usuaria.estado == EstadoUsuaria.activa)
    )).scalar()
    hoy = (await db.execute(
        select(func.count()).where(
            cast(Alerta.created_at, Date) == date.today()
        )
    )).scalar()
    mes = (await db.execute(
        select(func.count()).where(
            Alerta.created_at >= date.today().replace(day=1)
        )
    )).scalar()
    atendidas = (await db.execute(
        select(func.count()).where(Alerta.estado == EstadoAlerta.atendida)
    )).scalar()
    return DashboardStats(
        total_usuarias=total,
        usuarias_activas=activas,
        alertas_hoy=hoy,
        alertas_mes=mes,
        alertas_atendidas=atendidas,
    )

@router.get("/usuarias", response_model=list[UsuariaOut])
async def listar_usuarias(
    skip: int = 0, limit: int = 50,
    estado: str = None,
    db: AsyncSession = Depends(get_db)
):
    q = select(Usuaria).offset(skip).limit(limit).order_by(Usuaria.created_at.desc())
    if estado:
        q = q.where(Usuaria.estado == estado)
    res = await db.execute(q)
    return res.scalars().all()

@router.get("/alertas", response_model=list[AlertaOut])
async def listar_alertas(
    skip: int = 0, limit: int = 50,
    estado: str = None,
    db: AsyncSession = Depends(get_db)
):
    q = select(Alerta).offset(skip).limit(limit).order_by(Alerta.created_at.desc())
    if estado:
        q = q.where(Alerta.estado == estado)
    res = await db.execute(q)
    return res.scalars().all()

@router.patch("/alertas/{alerta_id}", response_model=AlertaOut)
async def actualizar_alerta(alerta_id: str, datos: AlertaUpdate, db: AsyncSession = Depends(get_db)):
    from fastapi import HTTPException
    res = await db.execute(select(Alerta).where(Alerta.id == alerta_id))
    alerta = res.scalar_one_or_none()
    if not alerta:
        raise HTTPException(status_code=404)
    if datos.estado:
        alerta.estado = datos.estado
    if datos.notas_admin is not None:
        alerta.notas_admin = datos.notas_admin
    await db.flush()
    return alerta
