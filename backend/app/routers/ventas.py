from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_permission, sucursal_scope, verificar_acceso_sucursal
from app.models.recetas import RecetaVersion
from app.models.ventas import Venta
from app.schemas.ventas import VentaCrear
from app.services import inventario_service, ventas_service

router = APIRouter(prefix="/api/ventas", tags=["Ventas y Rentabilidad"])


@router.get("", dependencies=[Depends(require_permission("ventas.leer"))])
def listar_ventas(db: Session = Depends(get_db), scope: int | None = Depends(sucursal_scope)):
    q = db.query(Venta)
    if scope is not None:
        q = q.filter(Venta.sucursal_id == scope)
    ventas = q.order_by(Venta.id.desc()).all()
    return [
        {
            "id": v.id,
            "sucursal_id": v.sucursal_id,
            "producto_id": v.producto_id,
            "cantidad_vendida": float(v.cantidad_vendida),
            "total_venta": float(v.total_venta),
        }
        for v in ventas
    ]


@router.post("", dependencies=[Depends(require_permission("ventas.escribir"))])
def registrar_venta(
    payload: VentaCrear, db: Session = Depends(get_db), scope: int | None = Depends(sucursal_scope)
):
    verificar_acceso_sucursal(payload.sucursal_id, scope)
    # Hallazgo N°5 (auditoría): resolver el almacén de la sucursal para poder descontar
    # el stock realmente vendido (mismo patrón que app/routers/mermas.py). Se hace commit
    # del almacén por separado para que su creación (si es la primera venta de esa
    # sucursal) no dependa de que la venta se complete.
    almacen = inventario_service.obtener_o_crear_almacen(db, payload.sucursal_id)
    db.commit()
    try:
        venta = ventas_service.registrar_venta(
            db,
            payload.sucursal_id,
            almacen.id,
            payload.producto_id,
            payload.cantidad_vendida,
            payload.total_venta,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"id": venta.id, "producto_id": venta.producto_id, "total_venta": float(venta.total_venta)}


@router.get("/rentabilidad-por-tienda", dependencies=[Depends(require_permission("ventas.leer"))])
def rentabilidad_por_tienda(
    sucursal_id: int, db: Session = Depends(get_db), scope: int | None = Depends(sucursal_scope)
):
    """Rentabilidad real: venta POS vs costo real ponderado del lote de producto terminado
    en almacén (costo real de producción: insumos + mano de obra + CIF, Hallazgo N°1/N°2 de
    auditoría). Los productos sin lotes con stock disponible en la tienda no tienen costo real
    verificable y quedan fuera del diccionario; ventas_service los marca como
    COSTO_NO_DISPONIBLE en vez de asumir costo cero."""
    verificar_acceso_sucursal(sucursal_id, scope)
    almacen = inventario_service.obtener_o_crear_almacen(db, sucursal_id)
    productos_vendidos = {r.producto_id for r in db.query(RecetaVersion).filter(RecetaVersion.activa.is_(True))}
    costos_unitarios: dict[int, float] = {}
    for producto_id in productos_vendidos:
        costo_real = inventario_service.costo_promedio(db, producto_id, almacen.id)
        if costo_real > 0:
            costos_unitarios[producto_id] = float(costo_real)
    return ventas_service.rentabilidad_por_tienda(db, costos_unitarios, sucursal_id)
