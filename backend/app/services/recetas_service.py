from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.recetas import RecetaIngrediente, RecetaVersion
from app.services import inventario_service


def crear_version_receta(
    db: Session,
    producto_id: int,
    rendimiento_unidades: float,
    ingredientes: list[dict],
    merma_estimada_pct: float = 0.0,
) -> RecetaVersion:
    """Crea una nueva versión de receta para un producto y desactiva la versión anterior activa."""
    anterior = (
        db.query(RecetaVersion)
        .filter(RecetaVersion.producto_id == producto_id, RecetaVersion.activa.is_(True))
        .first()
    )
    nueva_version = 1
    if anterior is not None:
        nueva_version = anterior.version + 1
        anterior.activa = False

    receta = RecetaVersion(
        producto_id=producto_id,
        version=nueva_version,
        rendimiento_unidades=rendimiento_unidades,
        merma_estimada_pct=merma_estimada_pct,
        activa=True,
    )
    db.add(receta)
    db.flush()

    for ing in ingredientes:
        db.add(
            RecetaIngrediente(
                receta_id=receta.id,
                insumo_id=ing["insumo_id"],
                cantidad_por_unidad=ing["cantidad_por_unidad"],
            )
        )
    db.commit()
    db.refresh(receta)
    return receta


def receta_activa(db: Session, producto_id: int) -> RecetaVersion | None:
    return (
        db.query(RecetaVersion)
        .filter(RecetaVersion.producto_id == producto_id, RecetaVersion.activa.is_(True))
        .first()
    )


class _CostoEstandar:
    def __init__(self, costo_unitario: Decimal):
        self.costo_unitario = costo_unitario


def calcular_costo_estandar(db: Session, producto_id: int, almacen_id: int) -> _CostoEstandar:
    """Calcula el costo estándar unitario del producto según su receta activa y el
    costo promedio actual de sus insumos en el almacén indicado (incluye merma estimada)."""
    receta = receta_activa(db, producto_id)
    if receta is None:
        raise ValueError("El producto no tiene receta activa")

    costo_insumos = Decimal("0")
    for ingrediente in receta.ingredientes:
        costo_prom = inventario_service.costo_promedio(db, ingrediente.insumo_id, almacen_id)
        costo_insumos += Decimal(str(ingrediente.cantidad_por_unidad)) * costo_prom

    merma_pct = Decimal(str(receta.merma_estimada_pct or 0))
    costo_con_merma = costo_insumos * (Decimal("1") + merma_pct)

    rendimiento = Decimal(str(receta.rendimiento_unidades or 1))
    costo_unitario = costo_con_merma / rendimiento if rendimiento > 0 else costo_con_merma
    return _CostoEstandar(costo_unitario)
