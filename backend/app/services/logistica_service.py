from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.logistica import Despacho, EstadoDespacho, RecepcionTienda
from app.models.produccion import EstadoOP, OrdenProduccion
from app.services import inventario_service, mermas_service, produccion_service


def crear_despacho(
    db: Session, op_id: int, responsable: str, vehiculo: str = ""
) -> Despacho:
    """Registra el despacho de una OP (responsable, vehículo, hora de salida) y
    avanza la OP de EMPAQUE -> DESPACHO. La OP debe estar en EMPAQUE."""
    op = db.query(OrdenProduccion).get(op_id)
    if op is None:
        raise ValueError("Orden de producción no encontrada")
    if EstadoOP(op.estado) != EstadoOP.EMPAQUE:
        raise ValueError(
            f"Solo se puede despachar una OP en estado EMPAQUE (estado actual: {op.estado})"
        )
    if not responsable:
        raise ValueError("El responsable del despacho es obligatorio")

    despacho = Despacho(
        op_id=op.id,
        sucursal_id=op.sucursal_id,
        responsable=responsable,
        vehiculo=vehiculo,
        estado=EstadoDespacho.EN_RUTA,
    )
    db.add(despacho)
    produccion_service.avanzar_estado(db, op_id=op.id, nuevo_estado=EstadoOP.DESPACHO.value)
    db.commit()
    db.refresh(despacho)
    return despacho


def registrar_recepcion(
    db: Session,
    despacho_id: int,
    cantidad_recepcionada: float,
    cantidad_merma: float = 0,
    aceptado: bool = True,
    observaciones: str = "",
) -> RecepcionTienda:
    """Registra la recepción en tienda de un despacho: cantidad aceptada, merma de
    transporte (se valoriza y descuenta del almacén de la tienda) y avanza la OP
    de DESPACHO -> RECEPCION."""
    despacho = db.query(Despacho).get(despacho_id)
    if despacho is None:
        raise ValueError("Despacho no encontrado")
    if despacho.recepcion is not None:
        raise ValueError("Este despacho ya tiene una recepción registrada")

    op = despacho.op
    if EstadoOP(op.estado) != EstadoOP.DESPACHO:
        raise ValueError(
            f"La OP asociada no está en estado DESPACHO (estado actual: {op.estado})"
        )

    if cantidad_merma and float(cantidad_merma) > 0:
        almacen = inventario_service.obtener_o_crear_almacen(db, despacho.sucursal_id)
        mermas_service.registrar_merma(
            db,
            producto_id=op.producto_id,
            almacen_id=almacen.id,
            cantidad=cantidad_merma,
            motivo=f"MERMA_TRANSPORTE-{op.codigo}",
        )

    recepcion = RecepcionTienda(
        despacho_id=despacho.id,
        cantidad_recepcionada=cantidad_recepcionada,
        cantidad_merma=cantidad_merma,
        aceptado=1 if aceptado else 0,
        observaciones=observaciones,
    )
    db.add(recepcion)
    despacho.estado = EstadoDespacho.ENTREGADO
    produccion_service.avanzar_estado(db, op_id=op.id, nuevo_estado=EstadoOP.RECEPCION.value)
    db.commit()
    db.refresh(recepcion)
    return recepcion


def listar_despachos(db: Session, sucursal_id: int | None = None) -> list[Despacho]:
    q = db.query(Despacho)
    if sucursal_id is not None:
        q = q.filter(Despacho.sucursal_id == sucursal_id)
    return q.order_by(Despacho.id.desc()).all()
