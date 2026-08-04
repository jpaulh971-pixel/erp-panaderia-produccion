"""Lean Manufacturing / Six Sigma / TOC sobre datos reales de producción.

Todo se calcula a partir de `historial_estado_op` (timestamp real de cada
transición) y de `cantidad_solicitada` / `cantidad_producida`. Donde el ERP
no captura el dato necesario para una métrica clásica de forma exacta (p.ej.
OEE separa unidades buenas/malas por lote, y aquí las mermas no están
enlazadas a una OP específica), se documenta la aproximación usada en vez de
inventar precisión que los datos no respaldan.
"""
import statistics
from collections import defaultdict
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.mermas import Merma
from app.models.produccion import EstadoOP, HistorialEstadoOP, OrdenProduccion

# Etapas que agregan transformación real al producto (tiempo de valor agregado).
ETAPAS_VALOR_AGREGADO = {EstadoOP.PRODUCCION, EstadoOP.HORNEADO, EstadoOP.EMPAQUE}


def _duraciones_por_etapa(db: Session) -> dict[int, list[dict]]:
    """Para cada OP, la lista de (estado, duración_en_segundos) que estuvo en
    cada etapa, calculada como la diferencia entre transiciones consecutivas
    reales del historial."""
    historial = (
        db.query(HistorialEstadoOP).order_by(HistorialEstadoOP.op_id, HistorialEstadoOP.id).all()
    )
    por_op: dict[int, list[HistorialEstadoOP]] = defaultdict(list)
    for h in historial:
        por_op[h.op_id].append(h)

    resultado: dict[int, list[dict]] = {}
    for op_id, eventos in por_op.items():
        tramos = []
        for i in range(len(eventos) - 1):
            actual, siguiente = eventos[i], eventos[i + 1]
            segundos = (siguiente.creado_en - actual.creado_en).total_seconds()
            tramos.append({"estado": actual.estado, "segundos": max(segundos, 0)})
        resultado[op_id] = tramos
    return resultado


def cuello_de_botella(db: Session) -> dict:
    """TOC: la etapa con mayor tiempo promedio de permanencia es la restricción
    del sistema (cuello de botella) — es la que hay que atacar primero."""
    tramos_por_op = _duraciones_por_etapa(db)
    segundos_por_estado: dict[str, list[float]] = defaultdict(list)
    for tramos in tramos_por_op.values():
        for tramo in tramos:
            segundos_por_estado[tramo["estado"].value].append(tramo["segundos"])

    etapas = []
    for estado, valores in segundos_por_estado.items():
        etapas.append(
            {
                "estado": estado,
                "tiempo_promedio_horas": (sum(valores) / len(valores)) / 3600 if valores else 0.0,
                "muestras": len(valores),
            }
        )
    etapas.sort(key=lambda e: e["tiempo_promedio_horas"], reverse=True)
    return {
        "etapas": etapas,
        "cuello_de_botella": etapas[0]["estado"] if etapas else None,
    }


def oee_aproximado(db: Session) -> dict:
    """OEE = Disponibilidad x Rendimiento x Calidad, con estas aproximaciones:

    - Rendimiento (Performance): promedio de cantidad_producida/cantidad_solicitada
      en OPs que ya pasaron por EMPAQUE.
    - Disponibilidad (Availability): proporción del lead time total que fue
      tiempo de transformación real (PRODUCCION+HORNEADO+EMPAQUE) vs. tiempo
      total de ciclo (incluye esperas/colas entre etapas).
    - Calidad (Quality): 1 - (valor de mermas / valor de lo producido), a
      nivel de planta (las mermas no están enlazadas a una OP específica en
      este modelo, así que no se puede calcular por lote).
    """
    ops = (
        db.query(OrdenProduccion)
        .filter(OrdenProduccion.cantidad_producida.isnot(None))
        .all()
    )
    if not ops:
        return {
            "oee_pct": None,
            "disponibilidad_pct": None,
            "rendimiento_pct": None,
            "calidad_pct": None,
            "mensaje": "Aún no hay OPs con producción registrada (etapa EMPAQUE o posterior).",
        }

    rendimientos = [
        min(float(op.cantidad_producida) / float(op.cantidad_solicitada), 1.0)
        for op in ops
        if float(op.cantidad_solicitada or 0) > 0
    ]
    rendimiento_pct = (sum(rendimientos) / len(rendimientos) * 100) if rendimientos else 0.0

    tramos_por_op = _duraciones_por_etapa(db)
    disponibilidades = []
    for op in ops:
        tramos = tramos_por_op.get(op.id, [])
        total = sum(t["segundos"] for t in tramos)
        valor_agregado = sum(t["segundos"] for t in tramos if t["estado"] in ETAPAS_VALOR_AGREGADO)
        if total > 0:
            disponibilidades.append(valor_agregado / total)
    disponibilidad_pct = (sum(disponibilidades) / len(disponibilidades) * 100) if disponibilidades else 0.0

    costo_producido_total = Decimal("0")
    for op in ops:
        if op.costo_real_total:
            costo_producido_total += Decimal(str(op.costo_real_total))
    valor_mermas = sum((Decimal(str(m.costo_valorizado)) for m in db.query(Merma).all()), Decimal("0"))
    if costo_producido_total > 0:
        calidad_pct = max(0.0, (1 - float(valor_mermas) / float(costo_producido_total)) * 100)
    else:
        calidad_pct = 100.0

    oee_pct = (disponibilidad_pct / 100) * (rendimiento_pct / 100) * (calidad_pct / 100) * 100

    return {
        "oee_pct": oee_pct,
        "disponibilidad_pct": disponibilidad_pct,
        "rendimiento_pct": rendimiento_pct,
        "calidad_pct": calidad_pct,
        "ops_analizadas": len(ops),
    }


def capacidad_proceso(db: Session, tolerancia_pct: float = 0.10) -> dict:
    """Six Sigma Cp/Cpk sobre el rendimiento de producción (cantidad_producida /
    cantidad_solicitada). Límites de especificación: 100% ± tolerancia_pct
    (por defecto ±10%), configurables porque no hay un límite de tolerancia
    de fábrica definido en el ERP todavía."""
    ops = (
        db.query(OrdenProduccion)
        .filter(OrdenProduccion.cantidad_producida.isnot(None))
        .all()
    )
    ratios = [
        float(op.cantidad_producida) / float(op.cantidad_solicitada)
        for op in ops
        if float(op.cantidad_solicitada or 0) > 0
    ]
    if len(ratios) < 2:
        return {
            "cp": None,
            "cpk": None,
            "mensaje": "Se necesitan al menos 2 OPs con producción registrada para calcular Cp/Cpk.",
            "muestras": len(ratios),
        }

    media = statistics.mean(ratios)
    desviacion = statistics.stdev(ratios)
    lsl = 1 - tolerancia_pct
    usl = 1 + tolerancia_pct

    if desviacion == 0:
        return {
            "cp": None,
            "cpk": None,
            "mensaje": "Desviación estándar es 0 (todas las OPs rindieron exactamente igual); Cp/Cpk no son calculables.",
            "media_rendimiento_pct": media * 100,
            "muestras": len(ratios),
        }

    cp = (usl - lsl) / (6 * desviacion)
    cpk = min(usl - media, media - lsl) / (3 * desviacion)

    if cpk >= 1.33:
        interpretacion = "Proceso capaz (Cpk ≥ 1.33)"
    elif cpk >= 1.0:
        interpretacion = "Proceso marginalmente capaz (1.0 ≤ Cpk < 1.33)"
    else:
        interpretacion = "Proceso NO capaz (Cpk < 1.0): alta variabilidad frente a la tolerancia"

    return {
        "cp": cp,
        "cpk": cpk,
        "media_rendimiento_pct": media * 100,
        "desviacion_estandar_pct": desviacion * 100,
        "limite_inferior_pct": lsl * 100,
        "limite_superior_pct": usl * 100,
        "interpretacion": interpretacion,
        "muestras": len(ratios),
    }


def tablero_kanban(db: Session) -> dict:
    """Conteo de OPs por estado, para visualizar el flujo Kanban del taller."""
    ops = db.query(OrdenProduccion).all()
    conteo: dict[str, int] = {e.value: 0 for e in EstadoOP}
    for op in ops:
        conteo[op.estado.value] += 1
    columnas = [{"estado": estado, "cantidad": cantidad} for estado, cantidad in conteo.items()]
    return {"columnas": columnas, "total_ops": len(ops)}
