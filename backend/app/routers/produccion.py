from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_permission, sucursal_scope, verificar_acceso_sucursal
from app.schemas.produccion import OPAvanzar, OPCrear, OPOut
from app.services import produccion_service

router = APIRouter(prefix="/api/produccion", tags=["Producción"])


@router.get("", response_model=list[OPOut], dependencies=[Depends(require_permission("inventario.leer"))])
def listar_ops(db: Session = Depends(get_db), scope: int | None = Depends(sucursal_scope)):
    from app.models.produccion import OrdenProduccion

    q = db.query(OrdenProduccion)
    if scope is not None:
        q = q.filter(OrdenProduccion.sucursal_id == scope)
    return q.order_by(OrdenProduccion.id.desc()).all()


@router.post("", response_model=OPOut, dependencies=[Depends(require_permission("produccion.escribir"))])
def crear_op(
    payload: OPCrear, db: Session = Depends(get_db), scope: int | None = Depends(sucursal_scope)
):
    verificar_acceso_sucursal(payload.sucursal_id, scope)
    try:
        return produccion_service.crear_op(
            db, payload.sucursal_id, payload.producto_id, payload.cantidad_solicitada
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/{op_id}/avanzar", response_model=OPOut, dependencies=[Depends(require_permission("produccion.escribir"))]
)
def avanzar_op(op_id: int, payload: OPAvanzar, db: Session = Depends(get_db)):
    try:
        return produccion_service.avanzar_estado(
            db, op_id, payload.nuevo_estado, payload.cantidad_producida
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
