from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_permission, sucursal_scope
from app.schemas.logistica import DespachoCrear, DespachoOut, RecepcionCrear, RecepcionOut
from app.services import logistica_service

router = APIRouter(prefix="/api/logistica", tags=["Despacho y Recepción"])


@router.get("/despachos", response_model=list[DespachoOut], dependencies=[Depends(require_permission("inventario.leer"))])
def listar_despachos(db: Session = Depends(get_db), scope: int | None = Depends(sucursal_scope)):
    return logistica_service.listar_despachos(db, sucursal_id=scope)


@router.post("/despachos", response_model=DespachoOut, dependencies=[Depends(require_permission("produccion.escribir"))])
def crear_despacho(payload: DespachoCrear, db: Session = Depends(get_db)):
    try:
        return logistica_service.crear_despacho(db, payload.op_id, payload.responsable, payload.vehiculo)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/recepciones", response_model=RecepcionOut, dependencies=[Depends(require_permission("produccion.escribir"))])
def registrar_recepcion(payload: RecepcionCrear, db: Session = Depends(get_db)):
    try:
        return logistica_service.registrar_recepcion(
            db,
            despacho_id=payload.despacho_id,
            cantidad_recepcionada=payload.cantidad_recepcionada,
            cantidad_merma=payload.cantidad_merma,
            aceptado=payload.aceptado,
            observaciones=payload.observaciones,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
