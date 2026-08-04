import re
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.inventario import TipoMovimiento
from app.models.organizacion import Sucursal
from app.models.produccion import SIGUIENTE_ESTADO, EstadoOP, HistorialEstadoOP, OrdenProduccion
from app.models.productos import Producto
from app.services import inventario_service, recetas_service

LABOR_PCT = Decimal("0.15")
CIF_PCT = Decimal("0.10")

STOPWORDS = {"DE", "LA", "EL", "Y", "DEL", "LOS", "LAS", "CON"}


def _slug_producto(nombre: str, largo: int = 8) -> str:
    palabras = [p.upper() for p in re.split(r"\s+", nombre.strip()) if p]
    palabras_utiles = [p for p in palabras if p not in STOPWORDS] or palabras
    texto = "".join(re.sub(r"[^A-Z0-9]", "", p) for p in palabras_utiles)
    return texto[:largo] or "PROD"


def _generar_codigo(db: Session, sucursal: Sucursal, producto: Producto) -> str:
    fecha_str = date.today().strftime("%Y%m%d")
    prefijo = f"OP-{sucursal.codigo}-{_slug_producto(producto.nombre)}-{fecha_str}-"
    ultimo = (
        db.query(OrdenProduccion)
        .filter(OrdenProduccion.codigo.like(f"{prefijo}%"))
        .order_by(OrdenProduccion.id.desc())
        .first()
    )
    correlativo = 1
    if ultimo:
        try:
            correlativo = int(ultimo.codigo.split("-")[-1]) + 1
        except ValueError:
            correlativo = 1
    return f"{prefijo}{correlativo:03d}"


def crear_op(
    db: Session, sucursal_id: int, producto_id: int, cantidad_solicitada: float
) -> OrdenProduccion:
    sucursal = db.query(Sucursal).get(sucursal_id)
    if sucursal is None:
        raise ValueError("Sucursal no encontrada")
    producto = db.query(Producto).get(producto_id)
    if producto is None:
        raise ValueError("Producto no encontrado")
    if recetas_service.receta_activa(db, producto_id) is None:
        raise ValueError("El producto no tiene receta activa; no se puede generar la OP")

    op = OrdenProduccion(
        codigo=_generar_codigo(db, sucursal, producto),
        sucursal_id=sucursal_id,
        producto_id=producto_id,
        cantidad_solicitada=cantidad_solicitada,
        estado=EstadoOP.SOLICITADA,
    )
    db.add(op)
    db.flush()
    db.add(HistorialEstadoOP(op_id=op.id, estado=EstadoOP.SOLICITADA))
    db.commit()
    db.refresh(op)
    return op


def avanzar_estado(
    db: Session,
    op_id: int,
    nuevo_estado: str,
    cantidad_producida: float | None = None,
) -> OrdenProduccion:
    op = db.query(OrdenProduccion).get(op_id)
    if op is None:
        raise ValueError("Orden de producción no encontrada")

    try:
        nuevo = EstadoOP(nuevo_estado)
    except ValueError:
        raise ValueError(f"Estado desconocido: {nuevo_estado}")

    estado_actual = EstadoOP(op.estado)
    esperado = SIGUIENTE_ESTADO.get(estado_actual)
    if esperado is None or nuevo != esperado:
        esperado_str = esperado.value if esperado else "(ninguno, ya está en estado final)"
        raise ValueError(
            f"Transición inválida: {estado_actual.value} → {nuevo_estado}. "
            f"El siguiente estado permitido es {esperado_str}"
        )

    almacen = inventario_service.obtener_o_crear_almacen(db, op.sucursal_id)

    if nuevo == EstadoOP.DOSIFICACION:
        # Consume los insumos de la receta activa según la cantidad solicitada (FEFO real).
        receta = recetas_service.receta_activa(db, op.producto_id)
        if receta is None:
            raise ValueError("El producto no tiene receta activa")

        costo_insumos = Decimal("0")
        for ingrediente in receta.ingredientes:
            cantidad_requerida = Decimal(str(ingrediente.cantidad_por_unidad)) * Decimal(
                str(op.cantidad_solicitada)
            )
            costo_insumos += inventario_service.consumir_fefo(
                db,
                producto_id=ingrediente.insumo_id,
                almacen_id=almacen.id,
                cantidad=cantidad_requerida,
                referencia=op.codigo,
            )
        op.costo_insumos_real = costo_insumos

    elif nuevo == EstadoOP.EMPAQUE:
        if cantidad_producida is None:
            raise ValueError("cantidad_producida es obligatoria para avanzar a EMPAQUE")
        op.cantidad_producida = cantidad_producida

        # Hallazgo N°1 (auditoría funcional): el lote de producto terminado debe
        # ingresar al inventario con el costo real completo (insumos + mano de
        # obra + CIF), no solo con costo_insumos_real. Se adelanta aquí el mismo
        # cálculo que antes se hacía recién en FACTURADO, reutilizando LABOR_PCT
        # y CIF_PCT ya definidos en este módulo.
        insumos_reales = Decimal(str(op.costo_insumos_real or 0))
        op.costo_real_total = insumos_reales * (Decimal("1") + LABOR_PCT + CIF_PCT)

        costo_unitario_ingreso = Decimal("0")
        if op.costo_real_total and float(cantidad_producida) > 0:
            costo_unitario_ingreso = op.costo_real_total / Decimal(str(cantidad_producida))

        inventario_service.ingresar_lote(
            db,
            producto_id=op.producto_id,
            almacen_id=almacen.id,
            cantidad=Decimal(str(cantidad_producida)),
            costo_unitario=costo_unitario_ingreso,
            referencia=op.codigo,
            tipo_movimiento=TipoMovimiento.INGRESO_PRODUCCION,
        )

    elif nuevo == EstadoOP.FACTURADO:
        # costo_real_total ya fue fijado en EMPAQUE (mismo momento en que se
        # valorizó el lote en inventario). No se recalcula silenciosamente acá:
        # solo se valida que siga alineado con costo_insumos_real; si no
        # coincide (ej. dato corregido a mano entre EMPAQUE y FACTURADO), se
        # detiene el avance en vez de sobrescribir el costo del lote ya emitido.
        insumos_reales = Decimal(str(op.costo_insumos_real or 0))
        costo_calculado = insumos_reales * (Decimal("1") + LABOR_PCT + CIF_PCT)
        if op.costo_real_total is None:
            op.costo_real_total = costo_calculado
        elif abs(Decimal(str(op.costo_real_total)) - costo_calculado) > Decimal("0.01"):
            raise ValueError(
                "costo_real_total ya fue fijado en EMPAQUE (S/ "
                f"{op.costo_real_total}) y no coincide con el recálculo actual "
                f"(S/ {costo_calculado}). El lote de inventario quedó valorizado "
                "con el monto de EMPAQUE; revisar manualmente antes de facturar."
            )

    op.estado = nuevo
    db.add(HistorialEstadoOP(op_id=op.id, estado=nuevo))
    db.commit()
    db.refresh(op)
    return op
