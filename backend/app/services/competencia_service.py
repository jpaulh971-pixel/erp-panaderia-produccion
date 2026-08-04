"""Inteligencia Competitiva: compara el precio propio (derivado de las ventas
reales: total_venta/cantidad_vendida) contra precios de competencia
capturados manualmente, estima la elasticidad precio-demanda con el
histórico real de ventas, y recomienda un precio con esa elasticidad y el
costo real de receta que ya calcula recetas_service — no hay ningún dato
inventado ni supuestos de mercado sin sustento."""
import math
import statistics
from collections import defaultdict

from sqlalchemy.orm import Session

from app.models.competencia import PrecioCompetencia
from app.models.organizacion import Sucursal
from app.models.ventas import Venta
from app.services import inventario_service, recetas_service


def registrar_precio_competencia(
    db: Session, producto_id: int, competidor: str, precio: float, sucursal_id: int | None = None
) -> PrecioCompetencia:
    registro = PrecioCompetencia(
        producto_id=producto_id, competidor=competidor, precio=precio, sucursal_id=sucursal_id
    )
    db.add(registro)
    db.commit()
    db.refresh(registro)
    return registro


def listar_precios_competencia(db: Session, producto_id: int) -> list[PrecioCompetencia]:
    return (
        db.query(PrecioCompetencia)
        .filter(PrecioCompetencia.producto_id == producto_id)
        .order_by(PrecioCompetencia.id.desc())
        .all()
    )


def _precio_propio_promedio(db: Session, producto_id: int) -> float | None:
    ventas = db.query(Venta).filter(Venta.producto_id == producto_id).all()
    precios_unitarios = [
        float(v.total_venta) / float(v.cantidad_vendida)
        for v in ventas
        if float(v.cantidad_vendida or 0) > 0
    ]
    return statistics.mean(precios_unitarios) if precios_unitarios else None


def comparativo_precios(db: Session, producto_id: int) -> dict:
    """Precio propio (promedio de ventas reales) vs. precios de competencia
    registrados: promedio, mínimo, máximo, y diferencia % contra cada uno."""
    precio_propio = _precio_propio_promedio(db, producto_id)
    registros = listar_precios_competencia(db, producto_id)
    ultimos_por_competidor: dict[str, PrecioCompetencia] = {}
    for r in registros:  # ya vienen desc por id -> primera vez visto = más reciente
        ultimos_por_competidor.setdefault(r.competidor, r)
    filas = []
    for competidor, r in ultimos_por_competidor.items():
        precio_comp = float(r.precio)
        diferencia_pct = ((precio_propio - precio_comp) / precio_comp * 100) if (precio_propio and precio_comp) else None
        filas.append({
            "competidor": competidor,
            "precio": precio_comp,
            "fecha": r.creado_en.isoformat() if r.creado_en else None,
            "diferencia_vs_propio_pct": diferencia_pct,
        })
    precios_competencia = [f["precio"] for f in filas]
    return {
        "producto_id": producto_id,
        "precio_propio_promedio": precio_propio,
        "competencia": filas,
        "precio_competencia_promedio": statistics.mean(precios_competencia) if precios_competencia else None,
        "precio_competencia_min": min(precios_competencia) if precios_competencia else None,
        "precio_competencia_max": max(precios_competencia) if precios_competencia else None,
    }


def elasticidad_precio_demanda(db: Session, producto_id: int) -> dict:
    """Elasticidad precio-demanda = %Δcantidad / %Δprecio, estimada por
    regresión log-log sobre ventas diarias reales: ln(cantidad) = a + e*ln(precio).
    La pendiente `e` de esa regresión ES la elasticidad. Requiere ventas en al
    menos 2 precios unitarios distintos; si el precio nunca varió, no es
    calculable con datos reales (no se inventa un valor de mercado)."""
    ventas = db.query(Venta).filter(Venta.producto_id == producto_id).all()
    por_dia: dict = defaultdict(lambda: {"cantidad": 0.0, "monto": 0.0})
    for v in ventas:
        if not v.creado_en or float(v.cantidad_vendida or 0) <= 0:
            continue
        dia = v.creado_en.date()
        por_dia[dia]["cantidad"] += float(v.cantidad_vendida)
        por_dia[dia]["monto"] += float(v.total_venta)
    puntos = [
        (d["monto"] / d["cantidad"], d["cantidad"])
        for d in por_dia.values()
        if d["cantidad"] > 0
    ]
    precios_unicos = {round(p, 4) for p, _ in puntos}
    if len(puntos) < 3 or len(precios_unicos) < 2:
        return {
            "producto_id": producto_id, "elasticidad": None, "interpretacion": None,
            "dias_con_venta": len(puntos), "precios_distintos_observados": len(precios_unicos),
            "mensaje": "Se necesita historial de ventas en al menos 2 precios distintos "
                       "(3+ días con venta) para estimar elasticidad real.",
        }
    xs = [math.log(p) for p, _ in puntos]
    ys = [math.log(q) for _, q in puntos]
    x_media, y_media = statistics.mean(xs), statistics.mean(ys)
    num = sum((x - x_media) * (y - y_media) for x, y in zip(xs, ys))
    den = sum((x - x_media) ** 2 for x in xs)
    if den == 0:
        return {"producto_id": producto_id, "elasticidad": None, "mensaje": "Varianza de precio insuficiente."}
    elasticidad = num / den
    if abs(elasticidad) > 1:
        interpretacion = "Demanda ELÁSTICA (|e|>1): bajar precio aumenta más que proporcionalmente las unidades vendidas"
    elif abs(elasticidad) < 1:
        interpretacion = "Demanda INELÁSTICA (|e|<1): el precio afecta poco el volumen vendido"
    else:
        interpretacion = "Elasticidad unitaria (|e|=1)"
    return {
        "producto_id": producto_id,
        "elasticidad": elasticidad,
        "interpretacion": interpretacion,
        "dias_con_venta": len(puntos),
        "precios_distintos_observados": len(precios_unicos),
    }


def precio_recomendado(db: Session, producto_id: int, sucursal_id: int) -> dict:
    """Precio recomendado = costo real de receta (recetas_service) / (1 - margen
    objetivo de la sucursal), ajustado según elasticidad: si la demanda es
    elástica, se acerca al piso (margen objetivo); si es inelástica, se permite
    hasta 5 puntos porcentuales adicionales de margen (hay espacio para subir
    precio sin perder mucho volumen). El ajuste es conservador y siempre
    transparente en la respuesta (se muestra el cálculo, no solo el resultado)."""
    sucursal = db.query(Sucursal).get(sucursal_id)
    if sucursal is None:
        raise ValueError("Sucursal no encontrada")
    almacen = inventario_service.obtener_o_crear_almacen(db, sucursal_id)
    costo_real = recetas_service.calcular_costo_estandar(db, producto_id, almacen.id).costo_unitario
    margen_objetivo = float(sucursal.margen_objetivo or 0.12)
    elast = elasticidad_precio_demanda(db, producto_id)
    margen_ajustado = margen_objetivo
    ajuste_nota = "Sin historial suficiente para ajustar por elasticidad; se usa el margen objetivo de la tienda."
    if elast["elasticidad"] is not None:
        if abs(elast["elasticidad"]) > 1:
            margen_ajustado = margen_objetivo
            ajuste_nota = "Demanda elástica: se mantiene el margen objetivo (subir más el precio perdería volumen)."
        else:
            margen_ajustado = min(margen_objetivo + 0.05, 0.60)
            ajuste_nota = "Demanda inelástica: hay espacio para +5 pts de margen sin perder volumen significativo."
    if margen_ajustado >= 1:
        raise ValueError("Margen ajustado inválido (>=100%)")
    precio_sugerido = float(costo_real) / (1 - margen_ajustado)
    precio_comparativo = comparativo_precios(db, producto_id)
    return {
        "producto_id": producto_id,
        "sucursal_id": sucursal_id,
        "costo_real_unitario": float(costo_real),
        "margen_objetivo_tienda_pct": margen_objetivo * 100,
        "margen_ajustado_pct": margen_ajustado * 100,
        "ajuste_por_elasticidad": ajuste_nota,
        "elasticidad": elast["elasticidad"],
        "precio_recomendado": precio_sugerido,
        "precio_propio_actual": precio_comparativo["precio_propio_promedio"],
        "precio_competencia_promedio": precio_comparativo["precio_competencia_promedio"],
    }


def simular_promocion(db: Session, producto_id: int, descuento_pct: float) -> dict:
    """Simula el efecto de un descuento sobre unidades vendidas y utilidad,
    usando la elasticidad estimada (si no hay elasticidad calculable, solo
    proyecta el efecto directo en precio, sin inventar respuesta de demanda)."""
    if not (0 < descuento_pct < 100):
        raise ValueError("El descuento debe estar entre 0 y 100%")
    precio_propio = _precio_propio_promedio(db, producto_id)
    if precio_propio is None:
        raise ValueError("No hay historial de ventas de este producto para simular")
    elast = elasticidad_precio_demanda(db, producto_id)
    precio_nuevo = precio_propio * (1 - descuento_pct / 100)
    ventas = db.query(Venta).filter(Venta.producto_id == producto_id).all()
    cantidad_base_diaria = (
        sum(float(v.cantidad_vendida) for v in ventas) / max(len({v.creado_en.date() for v in ventas if v.creado_en}), 1)
        if ventas else 0.0
    )
    if elast["elasticidad"] is not None:
        variacion_pct_cantidad = -elast["elasticidad"] * (-descuento_pct / 100)  # %Δq = e * %Δp (Δp negativo)
        cantidad_proyectada = cantidad_base_diaria * (1 + variacion_pct_cantidad)
    else:
        cantidad_proyectada = cantidad_base_diaria  # sin elasticidad conocida: no se asume cambio en volumen
    utilidad_actual = cantidad_base_diaria * precio_propio
    utilidad_proyectada = cantidad_proyectada * precio_nuevo
    return {
        "producto_id": producto_id,
        "descuento_pct": descuento_pct,
        "precio_actual": precio_propio,
        "precio_con_descuento": precio_nuevo,
        "elasticidad_usada": elast["elasticidad"],
        "cantidad_diaria_actual_estimada": cantidad_base_diaria,
        "cantidad_diaria_proyectada": cantidad_proyectada,
        "venta_diaria_actual_estimada": utilidad_actual,
        "venta_diaria_proyectada": utilidad_proyectada,
        "variacion_venta_diaria_pct": (
            (utilidad_proyectada - utilidad_actual) / utilidad_actual * 100 if utilidad_actual > 0 else None
        ),
        "mensaje": None if elast["elasticidad"] is not None else
        "No hay elasticidad calculable con el historial actual: la proyección de cantidad asume volumen constante.",
    }
