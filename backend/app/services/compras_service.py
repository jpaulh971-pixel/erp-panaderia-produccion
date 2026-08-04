from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.compras import EstadoOC, OrdenCompra, OrdenCompraItem
from app.models.inventario import TipoMovimiento
from app.services import inventario_service


def _generar_codigo_oc(db: Session) -> str:
    ultimo = db.query(OrdenCompra).order_by(OrdenCompra.id.desc()).first()
    correlativo = (ultimo.id + 1) if ultimo else 1
    return f"OC-{correlativo:05d}"


def crear_oc(db: Session, proveedor_id: int, sucursal_id: int, items: list[dict]) -> OrdenCompra:
    almacen = inventario_service.obtener_o_crear_almacen(db, sucursal_id)
    oc = OrdenCompra(
        codigo=_generar_codigo_oc(db),
        proveedor_id=proveedor_id,
        almacen_id=almacen.id,
        estado=EstadoOC.SOLICITADA,
    )
    db.add(oc)
    db.flush()
    for item in items:
        db.add(
            OrdenCompraItem(
                orden_id=oc.id,
                producto_id=item["producto_id"],
                cantidad=item["cantidad"],
                costo_unitario=item["costo_unitario"],
            )
        )
    db.commit()
    db.refresh(oc)
    return oc


def aprobar_oc(db: Session, oc_id: int) -> OrdenCompra:
    oc = db.query(OrdenCompra).get(oc_id)
    if oc is None:
        raise ValueError("Orden de compra no encontrada")
    if oc.estado != EstadoOC.SOLICITADA:
        raise ValueError(f"Sólo se puede aprobar una OC en estado SOLICITADA (actual: {oc.estado.value})")
    oc.estado = EstadoOC.APROBADA
    db.commit()
    db.refresh(oc)
    return oc


def recibir_oc(db: Session, oc_id: int) -> OrdenCompra:
    """Marca la OC como recibida e ingresa cada ítem como un lote de inventario nuevo (FIFO/FEFO)."""
    oc = db.query(OrdenCompra).get(oc_id)
    if oc is None:
        raise ValueError("Orden de compra no encontrada")
    if oc.estado != EstadoOC.APROBADA:
        raise ValueError(f"Sólo se puede recibir una OC en estado APROBADA (actual: {oc.estado.value})")

    for item in oc.items:
        inventario_service.ingresar_lote(
            db,
            producto_id=item.producto_id,
            almacen_id=oc.almacen_id,
            cantidad=Decimal(str(item.cantidad)),
            costo_unitario=Decimal(str(item.costo_unitario)),
            referencia=oc.codigo,
            tipo_movimiento=TipoMovimiento.INGRESO_COMPRA,
        )
    oc.estado = EstadoOC.RECIBIDA
    db.commit()
    db.refresh(oc)
    return oc


def sugerir_proveedor(db: Session, producto_id: int):
    """Sugiere el proveedor con el último costo unitario más bajo registrado para el producto."""
    item = (
        db.query(OrdenCompraItem)
        .filter(OrdenCompraItem.producto_id == producto_id)
        .order_by(OrdenCompraItem.costo_unitario.asc())
        .first()
    )
    if item is None:
        return None
    return item.orden.proveedor
