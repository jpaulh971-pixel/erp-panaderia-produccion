from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_permission, sucursal_scope, verificar_acceso_sucursal
from app.schemas.mermas import MermaCrear
from app.services import inventario_service, mermas_service

router = APIRouter(prefix="/api/mermas", tags=["Mermas"])


@router.post("", dependencies=[Depends(require_permission("mermas.escribir"))])
def registrar_merma(
    payload: MermaCrear, db: Session = Depends(get_db), scope: int | None = Depends(sucursal_scope)
):
    verificar_acceso_sucursal(payload.sucursal_id, scope)
    almacen = inventario_service.obtener_o_crear_almacen(db, payload.sucursal_id)
    db.commit()
    try:
        costo = mermas_service.registrar_merma(
            db, payload.producto_id, almacen.id, payload.cantidad, payload.motivo, payload.tipo_perdida
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "producto_id": payload.producto_id,
        "cantidad": payload.cantidad,
        "tipo_perdida": payload.tipo_perdida,
        "costo_valorizado": float(costo),
    }
