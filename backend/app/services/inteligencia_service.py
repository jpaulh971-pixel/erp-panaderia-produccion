"""Centro de Inteligencia Empresarial.

Cada pregunta del prompt original se resuelve con una función Python que
consulta los datos transaccionales reales — no hay generación de texto libre
ni un LLM de por medio: la "inteligencia" es el cálculo, no una respuesta
inventada. Cada función retorna datos estructurados listos para graficar y
un `respuesta` en texto ya armado para mostrar directo en el chat del panel.
"""
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.mermas import Merma
from app.models.organizacion import Sucursal
from app.models.produccion import EstadoOP, OrdenProduccion
from app.models.productos import Producto
from app.models.recetas import RecetaIngrediente, RecetaVersion
from app.models.ventas import Venta
from app.services import inventario_service, kpi_service, lean_service, recetas_service

PREGUNTAS_DISPONIBLES = [
    {"codigo": "producir_mañana", "texto": "¿Qué debo producir mañana?"},
    {"codigo": "tienda_vende_mas", "texto": "¿Qué tienda vende más?"},
    {"codigo": "tienda_mas_merma", "texto": "¿Qué tienda genera más merma?"},
    {"codigo": "producto_mas_rentable", "texto": "¿Cuál es el producto más rentable?"},
    {"codigo": "impacto_falta_insumo", "texto": "¿Cuánto dejaré de vender si falta un insumo?", "requiere": ["insumo_id"]},
    {"codigo": "costo_real_producto", "texto": "¿Cuál es el costo real de un producto?", "requiere": ["producto_id"]},
    {"codigo": "compra_proxima_semana", "texto": "¿Cuánto necesito comprar la próxima semana?"},
    {"codigo": "op_mayor_eficiencia", "texto": "¿Qué OP tuvo mayor utilidad/eficiencia?"},
    {"codigo": "cuello_de_botella", "texto": "¿Cuál fue el cuello de botella?"},
    {"codigo": "producto_retirar", "texto": "¿Qué producto conviene retirar?"},
    {"codigo": "ahorro_reduccion_merma", "texto": "¿Cuánto ahorraré si reduzco la merma un X%?", "requiere": ["porcentaje"]},
]


def producir_mañana(db: Session) -> dict:
    """Sugiere qué producir mañana por tienda: promedio de ventas diarias de
    los últimos 7 días por producto/tienda, comparado contra el stock actual
    del producto terminado en esa tienda."""
    hace_7_dias = datetime.utcnow() - timedelta(days=7)
    ventas_recientes = db.query(Venta).filter(Venta.creado_en >= hace_7_dias).all()

    demanda: dict[tuple[int, int], float] = defaultdict(float)
    for v in ventas_recientes:
        demanda[(v.sucursal_id, v.producto_id)] += float(v.cantidad_vendida)

    sugerencias = []
    for (sucursal_id, producto_id), total in demanda.items():
        promedio_diario = total / 7
        almacen = inventario_service.obtener_o_crear_almacen(db, sucursal_id)
        stock_actual = float(inventario_service.stock_disponible(db, producto_id, almacen.id))
        sugerido = max(promedio_diario - stock_actual, 0)
        if sugerido > 0:
            sucursal = db.query(Sucursal).get(sucursal_id)
            producto = db.query(Producto).get(producto_id)
            sugerencias.append(
                {
                    "sucursal_id": sucursal_id,
                    "sucursal_nombre": sucursal.nombre if sucursal else "?",
                    "producto_id": producto_id,
                    "producto_nombre": producto.nombre if producto else "?",
                    "demanda_promedio_diaria": round(promedio_diario, 2),
                    "stock_actual": round(stock_actual, 2),
                    "cantidad_sugerida": round(sugerido, 2),
                }
            )
    sugerencias.sort(key=lambda s: s["cantidad_sugerida"], reverse=True)

    if not sugerencias:
        texto = "No hay suficiente historial de ventas (últimos 7 días) para sugerir producción, o el stock actual ya cubre la demanda esperada."
    else:
        top = sugerencias[0]
        texto = (
            f"Prioridad: {top['cantidad_sugerida']} de {top['producto_nombre']} para "
            f"{top['sucursal_nombre']} (demanda promedio {top['demanda_promedio_diaria']}/día, "
            f"stock actual {top['stock_actual']}). Hay {len(sugerencias)} producto(s)-tienda con déficit."
        )
    return {"respuesta": texto, "detalle": sugerencias}


def tienda_vende_mas(db: Session) -> dict:
    ventas = db.query(Venta).all()
    total_por_sucursal: dict[int, float] = defaultdict(float)
    for v in ventas:
        total_por_sucursal[v.sucursal_id] += float(v.total_venta)
    if not total_por_sucursal:
        return {"respuesta": "Todavía no hay ventas registradas.", "detalle": []}

    ranking = sorted(
        (
            {
                "sucursal_id": sid,
                "sucursal_nombre": (db.query(Sucursal).get(sid).nombre if db.query(Sucursal).get(sid) else "?"),
                "total_venta": total,
            }
            for sid, total in total_por_sucursal.items()
        ),
        key=lambda x: x["total_venta"],
        reverse=True,
    )
    top = ranking[0]
    texto = f"{top['sucursal_nombre']} vende más, con S/ {top['total_venta']:.2f} acumulados."
    return {"respuesta": texto, "detalle": ranking}


def tienda_mas_merma(db: Session) -> dict:
    mermas = db.query(Merma).all()
    valor_por_sucursal: dict[int, float] = defaultdict(float)
    for m in mermas:
        sucursal_id = m.almacen.sucursal_id if m.almacen else None
        if sucursal_id:
            valor_por_sucursal[sucursal_id] += float(m.costo_valorizado)
    if not valor_por_sucursal:
        return {"respuesta": "Todavía no hay mermas registradas.", "detalle": []}

    ranking = sorted(
        (
            {
                "sucursal_id": sid,
                "sucursal_nombre": (db.query(Sucursal).get(sid).nombre if db.query(Sucursal).get(sid) else "?"),
                "valor_merma": v,
            }
            for sid, v in valor_por_sucursal.items()
        ),
        key=lambda x: x["valor_merma"],
        reverse=True,
    )
    top = ranking[0]
    texto = f"{top['sucursal_nombre']} genera más merma valorizada: S/ {top['valor_merma']:.2f}."
    return {"respuesta": texto, "detalle": ranking}


def producto_mas_rentable(db: Session) -> dict:
    resumen = kpi_service.resumen_ejecutivo(db)
    ranking = resumen["ranking_productos"]
    if not ranking:
        return {"respuesta": "Todavía no hay suficientes ventas para calcular rentabilidad por producto.", "detalle": []}
    top = ranking[0]
    texto = f"{top['producto_nombre']} es el producto más rentable, con S/ {top['utilidad_total']:.2f} de utilidad acumulada."
    return {"respuesta": texto, "detalle": ranking}


def impacto_falta_insumo(db: Session, insumo_id: int) -> dict:
    """Si un insumo se agota, ¿qué productos no se pueden fabricar y cuánta
    venta se perdería? Usa el precio de venta promedio histórico de cada
    producto afectado como estimador de la venta perdida."""
    insumo = db.query(Producto).get(insumo_id)
    if insumo is None:
        return {"respuesta": "Insumo no encontrado.", "detalle": []}

    ingredientes = db.query(RecetaIngrediente).filter(RecetaIngrediente.insumo_id == insumo_id).all()
    recetas_afectadas = [
        i.receta for i in ingredientes if i.receta.activa
    ]

    afectados = []
    for receta in recetas_afectadas:
        producto = receta.producto
        ventas_producto = db.query(Venta).filter(Venta.producto_id == producto.id).all()
        cantidad_total = sum(float(v.cantidad_vendida) for v in ventas_producto)
        venta_total = sum(float(v.total_venta) for v in ventas_producto)
        precio_promedio = (venta_total / cantidad_total) if cantidad_total > 0 else 0.0
        hace_7_dias = datetime.utcnow() - timedelta(days=7)
        demanda_semanal = sum(
            float(v.cantidad_vendida) for v in ventas_producto if v.creado_en and v.creado_en >= hace_7_dias
        )
        venta_semanal_en_riesgo = demanda_semanal * precio_promedio
        afectados.append(
            {
                "producto_id": producto.id,
                "producto_nombre": producto.nombre,
                "precio_promedio": round(precio_promedio, 2),
                "demanda_semanal_unidades": round(demanda_semanal, 2),
                "venta_semanal_en_riesgo": round(venta_semanal_en_riesgo, 2),
            }
        )
    afectados.sort(key=lambda a: a["venta_semanal_en_riesgo"], reverse=True)
    total_en_riesgo = sum(a["venta_semanal_en_riesgo"] for a in afectados)

    if not afectados:
        texto = f"Ningún producto con receta activa usa {insumo.nombre} como ingrediente."
    else:
        texto = (
            f"Si falta {insumo.nombre}, se afectan {len(afectados)} producto(s) — "
            f"venta semanal en riesgo estimada: S/ {total_en_riesgo:.2f}."
        )
    return {"respuesta": texto, "detalle": afectados}


def costo_real_producto(db: Session, producto_id: int) -> dict:
    producto = db.query(Producto).get(producto_id)
    if producto is None:
        return {"respuesta": "Producto no encontrado.", "detalle": None}

    ops_facturadas = (
        db.query(OrdenProduccion)
        .filter(OrdenProduccion.producto_id == producto_id, OrdenProduccion.estado == EstadoOP.FACTURADO)
        .all()
    )
    costos_unitarios_reales = [
        float(op.costo_real_total) / float(op.cantidad_producida)
        for op in ops_facturadas
        if op.costo_real_total and op.cantidad_producida and float(op.cantidad_producida) > 0
    ]
    costo_real_promedio = (
        sum(costos_unitarios_reales) / len(costos_unitarios_reales) if costos_unitarios_reales else None
    )

    costo_estandar = None
    receta = recetas_service.receta_activa(db, producto_id)
    if receta is not None:
        sucursal = db.query(Sucursal).first()
        if sucursal is not None:
            almacen = inventario_service.obtener_o_crear_almacen(db, sucursal.id)
            try:
                costo_estandar = float(recetas_service.calcular_costo_estandar(db, producto_id, almacen.id).costo_unitario)
            except ValueError:
                costo_estandar = None

    if costo_real_promedio is not None:
        texto = f"Costo real promedio de {producto.nombre} (sobre {len(costos_unitarios_reales)} OP facturadas): S/ {costo_real_promedio:.2f} por unidad."
    elif costo_estandar is not None:
        texto = f"Aún no hay OPs facturadas de {producto.nombre}; costo estándar según receta activa: S/ {costo_estandar:.2f} por unidad."
    else:
        texto = f"{producto.nombre} no tiene receta activa ni OPs facturadas para estimar costo."

    return {
        "respuesta": texto,
        "detalle": {
            "producto_nombre": producto.nombre,
            "costo_real_promedio": round(costo_real_promedio, 2) if costo_real_promedio else None,
            "costo_estandar_vigente": round(costo_estandar, 2) if costo_estandar else None,
            "ops_facturadas_analizadas": len(costos_unitarios_reales),
        },
    }


def compra_proxima_semana(db: Session) -> dict:
    """Necesidad de insumos para la próxima semana = demanda proyectada de
    productos terminados (promedio 7 días) explotada por receta activa,
    menos el stock de insumos ya disponible."""
    hace_7_dias = datetime.utcnow() - timedelta(days=7)
    ventas_recientes = db.query(Venta).filter(Venta.creado_en >= hace_7_dias).all()
    demanda_producto: dict[int, float] = defaultdict(float)
    for v in ventas_recientes:
        demanda_producto[v.producto_id] += float(v.cantidad_vendida)

    necesidad_insumo: dict[int, float] = defaultdict(float)
    for producto_id, cantidad in demanda_producto.items():
        receta = recetas_service.receta_activa(db, producto_id)
        if receta is None:
            continue
        for ing in receta.ingredientes:
            necesidad_insumo[ing.insumo_id] += float(ing.cantidad_por_unidad) * cantidad

    resultado = []
    for insumo_id, necesario in necesidad_insumo.items():
        stock_total = Decimal("0")
        for sucursal in db.query(Sucursal).all():
            almacen = inventario_service.obtener_o_crear_almacen(db, sucursal.id)
            stock_total += inventario_service.stock_disponible(db, insumo_id, almacen.id)
        faltante = max(necesario - float(stock_total), 0)
        if faltante > 0:
            insumo = db.query(Producto).get(insumo_id)
            resultado.append(
                {
                    "insumo_id": insumo_id,
                    "insumo_nombre": insumo.nombre if insumo else "?",
                    "unidad": insumo.unidad if insumo else "",
                    "necesidad_proyectada": round(necesario, 2),
                    "stock_actual_total": round(float(stock_total), 2),
                    "cantidad_a_comprar": round(faltante, 2),
                }
            )
    resultado.sort(key=lambda r: r["cantidad_a_comprar"], reverse=True)

    if not resultado:
        texto = "Con el stock actual y la demanda proyectada de la última semana, no se necesitan compras adicionales."
    else:
        texto = f"Se proyecta déficit en {len(resultado)} insumo(s) para la próxima semana; prioridad: {resultado[0]['insumo_nombre']} ({resultado[0]['cantidad_a_comprar']} {resultado[0]['unidad']})."
    return {"respuesta": texto, "detalle": resultado}


def op_mayor_eficiencia(db: Session) -> dict:
    """Entre las OP facturadas, la de menor costo real por unidad producida
    (mayor eficiencia). Nota: las ventas no están enlazadas a una OP
    específica en este modelo, así que 'utilidad por OP' se aproxima por
    eficiencia de costo, no por margen de venta real de ese lote."""
    ops = (
        db.query(OrdenProduccion)
        .filter(OrdenProduccion.estado == EstadoOP.FACTURADO, OrdenProduccion.costo_real_total.isnot(None))
        .all()
    )
    filas = []
    for op in ops:
        if not op.cantidad_producida or float(op.cantidad_producida) <= 0:
            continue
        costo_unitario = float(op.costo_real_total) / float(op.cantidad_producida)
        filas.append(
            {
                "op_id": op.id,
                "codigo": op.codigo,
                "producto_nombre": op.producto.nombre if op.producto else "?",
                "sucursal_nombre": op.sucursal.nombre if op.sucursal else "?",
                "costo_unitario_real": round(costo_unitario, 2),
                "cantidad_producida": float(op.cantidad_producida),
            }
        )
    filas.sort(key=lambda f: f["costo_unitario_real"])
    if not filas:
        return {"respuesta": "Todavía no hay OPs facturadas para comparar eficiencia.", "detalle": []}
    top = filas[0]
    texto = f"{top['codigo']} ({top['producto_nombre']}, {top['sucursal_nombre']}) es la más eficiente: S/ {top['costo_unitario_real']:.2f} por unidad."
    return {"respuesta": texto, "detalle": filas}


def cuello_de_botella_pregunta(db: Session) -> dict:
    resultado = lean_service.cuello_de_botella(db)
    if not resultado["etapas"]:
        return {"respuesta": "Aún no hay suficiente historial de producción para identificar el cuello de botella.", "detalle": resultado}
    texto = f"El cuello de botella actual es la etapa {resultado['cuello_de_botella']}, con {resultado['etapas'][0]['tiempo_promedio_horas']:.1f} horas promedio de permanencia."
    return {"respuesta": texto, "detalle": resultado}


def producto_retirar(db: Session) -> dict:
    resumen = kpi_service.resumen_ejecutivo(db)
    ranking = resumen["ranking_productos"]
    candidatos = [r for r in ranking if r["utilidad_total"] < 0]
    if not candidatos:
        if not ranking:
            return {"respuesta": "No hay suficientes datos de ventas para evaluar qué producto retirar.", "detalle": []}
        peor = ranking[-1]
        texto = f"Ningún producto está en pérdida real; el de menor utilidad relativa es {peor['producto_nombre']} (S/ {peor['utilidad_total']:.2f})."
        return {"respuesta": texto, "detalle": ranking[-3:]}
    peor = min(candidatos, key=lambda c: c["utilidad_total"])
    texto = f"Conviene evaluar retirar {peor['producto_nombre']}: pérdida acumulada de S/ {abs(peor['utilidad_total']):.2f}."
    return {"respuesta": texto, "detalle": candidatos}


def ahorro_reduccion_merma(db: Session, porcentaje: float) -> dict:
    mermas = db.query(Merma).all()
    valor_total = float(sum(Decimal(str(m.costo_valorizado)) for m in mermas))
    ahorro = valor_total * (porcentaje / 100)
    texto = f"Si reduces la merma un {porcentaje}%, ahorrarías aproximadamente S/ {ahorro:.2f} (sobre S/ {valor_total:.2f} de merma histórica valorizada)."
    return {"respuesta": texto, "detalle": {"merma_valorizada_total": valor_total, "ahorro_estimado": ahorro, "porcentaje": porcentaje}}
