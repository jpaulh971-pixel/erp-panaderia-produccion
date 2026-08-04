from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.inventario import Almacen, LoteInventario, MovimientoInventario, TipoMovimiento
from app.models.organizacion import Sucursal


def obtener_o_crear_almacen(db: Session, sucursal_id: int) -> Almacen:
    almacen = db.query(Almacen).filter(Almacen.sucursal_id == sucursal_id).first()
    if almacen is not None:
        return almacen
    sucursal = db.query(Sucursal).get(sucursal_id)
    if sucursal is None:
        raise ValueError("Sucursal no encontrada")
    almacen = Almacen(sucursal_id=sucursal_id, nombre=f"Almacén {sucursal.nombre}")
    db.add(almacen)
    db.flush()
    return almacen


def ingresar_lote(
    db: Session,
    producto_id: int,
    almacen_id: int,
    cantidad: Decimal,
    costo_unitario: Decimal,
    referencia: str = "",
    tipo_movimiento: TipoMovimiento = TipoMovimiento.INGRESO_COMPRA,
    fecha_vencimiento=None,
) -> LoteInventario:
    """Crea un nuevo lote de inventario y registra el movimiento en el kardex."""
    ultimo = (
        db.query(LoteInventario)
        .filter(LoteInventario.producto_id == producto_id, LoteInventario.almacen_id == almacen_id)
        .order_by(LoteInventario.id.desc())
        .first()
    )
    correlativo = (ultimo.id + 1) if ultimo else 1
    lote = LoteInventario(
        producto_id=producto_id,
        almacen_id=almacen_id,
        codigo_lote=f"LOTE-{producto_id}-{correlativo:05d}",
        cantidad_disponible=cantidad,
        costo_unitario=costo_unitario,
        referencia=referencia,
        fecha_vencimiento=fecha_vencimiento,
    )
    db.add(lote)
    db.flush()

    movimiento = MovimientoInventario(
        producto_id=producto_id,
        almacen_id=almacen_id,
        tipo=tipo_movimiento,
        cantidad=cantidad,
        costo_unitario=costo_unitario,
        costo_total=Decimal(str(cantidad)) * Decimal(str(costo_unitario)),
        referencia=referencia,
    )
    db.add(movimiento)
    db.flush()
    return lote


def consumir_fefo(
    db: Session,
    producto_id: int,
    almacen_id: int,
    cantidad: Decimal,
    referencia: str = "",
    tipo_movimiento: TipoMovimiento = TipoMovimiento.SALIDA_CONSUMO,
) -> Decimal:
    """Consume stock siguiendo PEPS/FEFO real: primero vencimiento más próximo,
    luego fecha de ingreso más antigua. Devuelve el costo valorizado total consumido.
    Lanza ValueError si no hay stock suficiente."""
    necesario = Decimal(str(cantidad))
    if necesario <= 0:
        return Decimal("0")

    lotes = (
        db.query(LoteInventario)
        .filter(
            LoteInventario.producto_id == producto_id,
            LoteInventario.almacen_id == almacen_id,
            LoteInventario.cantidad_disponible > 0,
        )
        .order_by(
            LoteInventario.fecha_vencimiento.is_(None),
            LoteInventario.fecha_vencimiento.asc(),
            LoteInventario.fecha_ingreso.asc(),
            LoteInventario.id.asc(),
        )
        .all()
    )

    disponible_total = sum((Decimal(str(l.cantidad_disponible)) for l in lotes), Decimal("0"))
    if disponible_total < necesario:
        raise ValueError(
            f"Stock insuficiente para el producto {producto_id} en el almacén {almacen_id}: "
            f"disponible {disponible_total}, requerido {necesario}"
        )

    costo_total = Decimal("0")
    restante = necesario
    for lote in lotes:
        if restante <= 0:
            break
        disponible_lote = Decimal(str(lote.cantidad_disponible))
        tomar = min(disponible_lote, restante)
        lote.cantidad_disponible = disponible_lote - tomar
        costo_unitario = Decimal(str(lote.costo_unitario))
        costo_total += tomar * costo_unitario
        restante -= tomar

        db.add(
            MovimientoInventario(
                producto_id=producto_id,
                almacen_id=almacen_id,
                tipo=tipo_movimiento,
                cantidad=-tomar,
                costo_unitario=costo_unitario,
                costo_total=-(tomar * costo_unitario),
                referencia=referencia,
            )
        )

    db.flush()
    return costo_total


def sugerir_lote_fefo(db: Session, producto_id: int, almacen_id: int) -> LoteInventario | None:
    """Solo lectura: indica cuál sería el próximo lote a consumir bajo FEFO/PEPS
    (vencimiento más próximo, luego ingreso más antiguo), sin descontar stock.
    Se usa para imprimir la hoja de dosificación antes de producir."""
    return (
        db.query(LoteInventario)
        .filter(
            LoteInventario.producto_id == producto_id,
            LoteInventario.almacen_id == almacen_id,
            LoteInventario.cantidad_disponible > 0,
        )
        .order_by(
            LoteInventario.fecha_vencimiento.is_(None),
            LoteInventario.fecha_vencimiento.asc(),
            LoteInventario.fecha_ingreso.asc(),
            LoteInventario.id.asc(),
        )
        .first()
    )


def stock_disponible(db: Session, producto_id: int, almacen_id: int) -> Decimal:
    lotes = (
        db.query(LoteInventario)
        .filter(LoteInventario.producto_id == producto_id, LoteInventario.almacen_id == almacen_id)
        .all()
    )
    return sum((Decimal(str(l.cantidad_disponible)) for l in lotes), Decimal("0"))


def costo_promedio(db: Session, producto_id: int, almacen_id: int) -> Decimal:
    lotes = (
        db.query(LoteInventario)
        .filter(
            LoteInventario.producto_id == producto_id,
            LoteInventario.almacen_id == almacen_id,
            LoteInventario.cantidad_disponible > 0,
        )
        .all()
    )
    cantidad_total = sum((Decimal(str(l.cantidad_disponible)) for l in lotes), Decimal("0"))
    if cantidad_total <= 0:
        return Decimal("0")
    valor_total = sum(
        (Decimal(str(l.cantidad_disponible)) * Decimal(str(l.costo_unitario)) for l in lotes), Decimal("0")
    )
    return valor_total / cantidad_total
