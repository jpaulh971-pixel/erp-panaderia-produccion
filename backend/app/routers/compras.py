from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_permission
from app.schemas.compras import OrdenCompraCrear, OrdenCompraOut
from app.services import compras_service

router = APIRouter(prefix="/api/compras", tags=["Compras"])


@router.get("", response_model=list[OrdenCompraOut], dependencies=[Depends(require_permission("inventario.leer"))])
def listar_ordenes_compra(db: Session = Depends(get_db)):
    from app.models.compras import OrdenCompra

    return db.query(OrdenCompra).order_by(OrdenCompra.id.desc()).all()


@router.post("", response_model=OrdenCompraOut, dependencies=[Depends(require_permission("compras.escribir"))])
def crear_orden_compra(payload: OrdenCompraCrear, db: Session = Depends(get_db)):
    try:
        oc = compras_service.crear_oc(
            db, payload.proveedor_id, payload.sucursal_id, [i.model_dump() for i in payload.items]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return oc


@router.post(
    "/{oc_id}/aprobar", response_model=OrdenCompraOut, dependencies=[Depends(require_permission("compras.escribir"))]
)
def aprobar_orden_compra(oc_id: int, db: Session = Depends(get_db)):
    try:
        return compras_service.aprobar_oc(db, oc_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/{oc_id}/recibir",
    response_model=OrdenCompraOut,
    dependencies=[Depends(require_permission("compras.escribir"))],
)
def recibir_orden_compra(oc_id: int, db: Session = Depends(get_db)):
    try:
        return compras_service.recibir_oc(db, oc_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
