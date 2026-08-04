from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_permission, sucursal_scope, verificar_acceso_sucursal
from app.models.inventario import Almacen, LoteInventario
from app.models.mermas import Merma
from app.services import inventario_service  # noqa: F401  (reservado para futuras consultas)

router = APIRouter(prefix="/api/consultas", tags=["Consultas"])


@router.get("/mermas", dependencies=[Depends(require_permission("inventario.leer"))])
def listar_mermas(db: Session = Depends(get_db), scope: int | None = Depends(sucursal_scope)):
    q = db.query(Merma)
    if scope is not None:
        q = q.join(Almacen, Merma.almacen_id == Almacen.id).filter(Almacen.sucursal_id == scope)
    mermas = q.order_by(Merma.id.desc()).all()
    return [
        {
            "id": m.id,
            "producto_id": m.producto_id,
            "almacen_id": m.almacen_id,
            "cantidad": float(m.cantidad),
            "motivo": m.motivo,
            "costo_valorizado": float(m.costo_valorizado),
        }
        for m in mermas
    ]


@router.get("/stock/{sucursal_id}", dependencies=[Depends(require_permission("inventario.leer"))])
def stock_por_sucursal(
    sucursal_id: int, db: Session = Depends(get_db), scope: int | None = Depends(sucursal_scope)
):
    """Stock disponible por producto en el almacén de la sucursal (para el dashboard)."""
    verificar_acceso_sucursal(sucursal_id, scope)
    almacen = db.query(Almacen).filter(Almacen.sucursal_id == sucursal_id).first()
    if almacen is None:
        return []
    lotes = (
        db.query(LoteInventario)
        .filter(LoteInventario.almacen_id == almacen.id, LoteInventario.cantidad_disponible > 0)
        .all()
    )
    por_producto: dict[int, dict] = {}
    for lote in lotes:
        d = por_producto.setdefault(
            lote.producto_id,
            {
                "producto_id": lote.producto_id,
                "producto_nombre": lote.producto.nombre,
                "unidad": lote.producto.unidad,
                "cantidad_disponible": 0.0,
                "valor_total": 0.0,
            },
        )
        d["cantidad_disponible"] += float(lote.cantidad_disponible)
        d["valor_total"] += float(lote.cantidad_disponible) * float(lote.costo_unitario)
    return sorted(por_producto.values(), key=lambda x: x["producto_nombre"])
