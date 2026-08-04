from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_permission
from app.schemas.competencia import PrecioCompetenciaCrear, SimularPromocion
from app.services import competencia_service

router = APIRouter(prefix="/api/competencia", tags=["Inteligencia Competitiva"])


@router.post("/precios", dependencies=[Depends(require_permission("ventas.escribir"))])
def registrar_precio(payload: PrecioCompetenciaCrear, db: Session = Depends(get_db)):
    return competencia_service.registrar_precio_competencia(
        db, payload.producto_id, payload.competidor, payload.precio, payload.sucursal_id
    )


@router.get("/comparativo/{producto_id}", dependencies=[Depends(require_permission("ventas.leer"))])
def comparativo_precios(producto_id: int, db: Session = Depends(get_db)):
    return competencia_service.comparativo_precios(db, producto_id)


@router.get("/elasticidad/{producto_id}", dependencies=[Depends(require_permission("ventas.leer"))])
def elasticidad(producto_id: int, db: Session = Depends(get_db)):
    return competencia_service.elasticidad_precio_demanda(db, producto_id)


@router.get("/precio-recomendado/{producto_id}", dependencies=[Depends(require_permission("ventas.leer"))])
def precio_recomendado(producto_id: int, sucursal_id: int, db: Session = Depends(get_db)):
    try:
        return competencia_service.precio_recomendado(db, producto_id, sucursal_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/simular-promocion", dependencies=[Depends(require_permission("ventas.leer"))])
def simular_promocion(payload: SimularPromocion, db: Session = Depends(get_db)):
    try:
        return competencia_service.simular_promocion(db, payload.producto_id, payload.descuento_pct)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
