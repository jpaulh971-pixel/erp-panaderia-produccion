from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.inventario import TipoMovimiento
from app.models.mermas import Merma, TipoPerdida
from app.models.productos import Producto
from app.services import inventario_service


def registrar_merma(
    db: Session,
    producto_id: int,
    almacen_id: int,
    cantidad: float,
    motivo: str = "",
    tipo_perdida: TipoPerdida = TipoPerdida.MERMA,
) -> Decimal:
    """Da de baja stock por merma (rotura, vencimiento, error de conteo, etc.),
    consumiendo vía FEFO y valorizando la pérdida al costo promedio de los lotes usados."""
    producto = db.query(Producto).get(producto_id)
    if producto is None:
        raise ValueError("Producto no encontrado")

    costo = inventario_service.consumir_fefo(
        db,
        producto_id=producto_id,
        almacen_id=almacen_id,
        cantidad=Decimal(str(cantidad)),
        referencia=motivo or "MERMA",
        tipo_movimiento=TipoMovimiento.SALIDA_MERMA,
    )

    merma = Merma(
        producto_id=producto_id,
        almacen_id=almacen_id,
        cantidad=cantidad,
        motivo=motivo,
        tipo_perdida=tipo_perdida,
        costo_valorizado=costo,
    )
    db.add(merma)
    db.commit()
    return costo
