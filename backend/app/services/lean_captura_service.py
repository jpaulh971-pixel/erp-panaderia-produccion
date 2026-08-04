"""Cálculos sobre los módulos Lean de captura: puntaje 5S, avance Kaizen,
% de mejora SMED, tiempo de respuesta Andon, cumplimiento Heijunka y %VA
del VSM. Todo se deriva de los registros reales que el equipo de planta
guarda con cada endpoint POST — no hay valores inventados."""
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.lean_captura import (
    AndonAlerta,
    Auditoria5S,
    EstadoAndon,
    EstadoKaizen,
    HeijunkaPlan,
    JidokaEvento,
    KaizenPropuesta,
    SmedRegistro,
    VsmPaso,
)


# ---------- 5S ----------
def registrar_auditoria_5s(
    db: Session, sucursal_id: int, area: str, seiri: int, seiton: int, seiso: int,
    seiketsu: int, shitsuke: int, observaciones: str = "", auditor: str = "",
) -> Auditoria5S:
    for nombre, valor in [("seiri", seiri), ("seiton", seiton), ("seiso", seiso),
                           ("seiketsu", seiketsu), ("shitsuke", shitsuke)]:
        if not (0 <= valor <= 5):
            raise ValueError(f"El puntaje de {nombre} debe estar entre 0 y 5")
    auditoria = Auditoria5S(
        sucursal_id=sucursal_id, area=area, seiri=seiri, seiton=seiton, seiso=seiso,
        seiketsu=seiketsu, shitsuke=shitsuke, observaciones=observaciones, auditor=auditor,
    )
    db.add(auditoria)
    db.commit()
    db.refresh(auditoria)
    return auditoria


def listar_auditorias_5s(db: Session, sucursal_id: int | None = None) -> list[Auditoria5S]:
    q = db.query(Auditoria5S)
    if sucursal_id is not None:
        q = q.filter(Auditoria5S.sucursal_id == sucursal_id)
    return q.order_by(Auditoria5S.id.desc()).all()


def resumen_5s(db: Session, sucursal_id: int | None = None) -> dict:
    """Puntaje 5S = promedio de las 5 eses / 5 * 100, promediado sobre las
    auditorías más recientes por área (la última auditoría de cada área)."""
    auditorias = listar_auditorias_5s(db, sucursal_id)
    ultima_por_area: dict[str, Auditoria5S] = {}
    for a in auditorias:  # ya vienen ordenadas desc por id => la primera vista por área es la más reciente
        ultima_por_area.setdefault(a.area, a)
    filas = []
    for area, a in ultima_por_area.items():
        puntaje = (a.seiri + a.seiton + a.seiso + a.seiketsu + a.shitsuke) / 5 / 5 * 100
        filas.append({
            "area": area,
            "puntaje_pct": puntaje,
            "fecha": a.creado_en.isoformat() if a.creado_en else None,
            "detalle": {"seiri": a.seiri, "seiton": a.seiton, "seiso": a.seiso,
                        "seiketsu": a.seiketsu, "shitsuke": a.shitsuke},
        })
    filas.sort(key=lambda f: f["puntaje_pct"])
    promedio_general = sum(f["puntaje_pct"] for f in filas) / len(filas) if filas else None
    return {"areas": filas, "promedio_general_pct": promedio_general, "auditorias_totales": len(auditorias)}


# ---------- Kaizen ----------
def crear_kaizen(
    db: Session, sucursal_id: int, area: str, titulo: str, descripcion: str = "",
    responsable: str = "", ahorro_estimado: float | None = None,
) -> KaizenPropuesta:
    propuesta = KaizenPropuesta(
        sucursal_id=sucursal_id, area=area, titulo=titulo, descripcion=descripcion,
        responsable=responsable, ahorro_estimado=ahorro_estimado,
    )
    db.add(propuesta)
    db.commit()
    db.refresh(propuesta)
    return propuesta


def listar_kaizen(db: Session, sucursal_id: int | None = None) -> list[KaizenPropuesta]:
    q = db.query(KaizenPropuesta)
    if sucursal_id is not None:
        q = q.filter(KaizenPropuesta.sucursal_id == sucursal_id)
    return q.order_by(KaizenPropuesta.id.desc()).all()


def avanzar_kaizen(db: Session, kaizen_id: int, nuevo_estado: EstadoKaizen) -> KaizenPropuesta:
    propuesta = db.query(KaizenPropuesta).get(kaizen_id)
    if propuesta is None:
        raise ValueError("Propuesta Kaizen no encontrada")
    propuesta.estado = nuevo_estado
    propuesta.actualizado_en = datetime.utcnow()
    db.commit()
    db.refresh(propuesta)
    return propuesta


def resumen_kaizen(db: Session, sucursal_id: int | None = None) -> dict:
    propuestas = listar_kaizen(db, sucursal_id)
    por_estado: dict[str, int] = {e.value: 0 for e in EstadoKaizen}
    ahorro_implementado = Decimal("0")
    for p in propuestas:
        por_estado[p.estado.value] += 1
        if p.estado == EstadoKaizen.IMPLEMENTADA and p.ahorro_estimado:
            ahorro_implementado += Decimal(str(p.ahorro_estimado))
    return {
        "por_estado": por_estado,
        "total": len(propuestas),
        "ahorro_implementado_total": float(ahorro_implementado),
    }


# ---------- SMED ----------
def registrar_smed(
    db: Session, sucursal_id: int, proceso: str, tiempo_setup_antes_min: float,
    tiempo_setup_despues_min: float | None = None, tiempo_interno_min: float | None = None,
    tiempo_externo_min: float | None = None, responsable: str = "",
) -> SmedRegistro:
    registro = SmedRegistro(
        sucursal_id=sucursal_id, proceso=proceso, tiempo_setup_antes_min=tiempo_setup_antes_min,
        tiempo_setup_despues_min=tiempo_setup_despues_min, tiempo_interno_min=tiempo_interno_min,
        tiempo_externo_min=tiempo_externo_min, responsable=responsable,
    )
    db.add(registro)
    db.commit()
    db.refresh(registro)
    return registro


def listar_smed(db: Session, sucursal_id: int | None = None) -> list[SmedRegistro]:
    q = db.query(SmedRegistro)
    if sucursal_id is not None:
        q = q.filter(SmedRegistro.sucursal_id == sucursal_id)
    return q.order_by(SmedRegistro.id.desc()).all()


def resumen_smed(db: Session, sucursal_id: int | None = None) -> list[dict]:
    """% de reducción de tiempo de setup por proceso = (antes - después) / antes."""
    filas = []
    for r in listar_smed(db, sucursal_id):
        antes = float(r.tiempo_setup_antes_min)
        despues = float(r.tiempo_setup_despues_min) if r.tiempo_setup_despues_min is not None else None
        mejora_pct = ((antes - despues) / antes * 100) if (despues is not None and antes > 0) else None
        filas.append({
            "id": r.id,
            "proceso": r.proceso,
            "tiempo_setup_antes_min": antes,
            "tiempo_setup_despues_min": despues,
            "mejora_pct": mejora_pct,
            "tiempo_interno_min": float(r.tiempo_interno_min) if r.tiempo_interno_min is not None else None,
            "tiempo_externo_min": float(r.tiempo_externo_min) if r.tiempo_externo_min is not None else None,
            "fecha": r.creado_en.isoformat() if r.creado_en else None,
        })
    return filas


# ---------- Jidoka ----------
def registrar_jidoka(
    db: Session, sucursal_id: int, etapa: str, motivo_paro: str,
    op_id: int | None = None, tiempo_paro_min: float | None = None,
) -> JidokaEvento:
    evento = JidokaEvento(
        sucursal_id=sucursal_id, op_id=op_id, etapa=etapa, motivo_paro=motivo_paro,
        tiempo_paro_min=tiempo_paro_min,
    )
    db.add(evento)
    db.commit()
    db.refresh(evento)
    return evento


def resolver_jidoka(db: Session, evento_id: int, accion_correctiva: str = "") -> JidokaEvento:
    evento = db.query(JidokaEvento).get(evento_id)
    if evento is None:
        raise ValueError("Evento Jidoka no encontrado")
    if evento.resuelto:
        raise ValueError("Este evento ya está resuelto")
    evento.resuelto = True
    evento.accion_correctiva = accion_correctiva
    evento.resuelto_en = datetime.utcnow()
    db.commit()
    db.refresh(evento)
    return evento


def listar_jidoka(db: Session, sucursal_id: int | None = None) -> list[JidokaEvento]:
    q = db.query(JidokaEvento)
    if sucursal_id is not None:
        q = q.filter(JidokaEvento.sucursal_id == sucursal_id)
    return q.order_by(JidokaEvento.id.desc()).all()


def resumen_jidoka(db: Session, sucursal_id: int | None = None) -> dict:
    eventos = listar_jidoka(db, sucursal_id)
    por_etapa: dict[str, int] = {}
    for e in eventos:
        por_etapa[e.etapa] = por_etapa.get(e.etapa, 0) + 1
    pendientes = sum(1 for e in eventos if not e.resuelto)
    return {
        "total_eventos": len(eventos),
        "pendientes": pendientes,
        "paros_por_etapa": sorted(
            [{"etapa": k, "paros": v} for k, v in por_etapa.items()], key=lambda x: x["paros"], reverse=True
        ),
    }


# ---------- Andon ----------
def crear_andon(db: Session, sucursal_id: int, etapa: str, tipo, descripcion: str = "") -> AndonAlerta:
    alerta = AndonAlerta(sucursal_id=sucursal_id, etapa=etapa, tipo=tipo, descripcion=descripcion)
    db.add(alerta)
    db.commit()
    db.refresh(alerta)
    return alerta


def resolver_andon(db: Session, alerta_id: int) -> AndonAlerta:
    alerta = db.query(AndonAlerta).get(alerta_id)
    if alerta is None:
        raise ValueError("Alerta Andon no encontrada")
    if alerta.estado == EstadoAndon.RESUELTA:
        raise ValueError("Esta alerta ya está resuelta")
    alerta.estado = EstadoAndon.RESUELTA
    alerta.resuelto_en = datetime.utcnow()
    db.commit()
    db.refresh(alerta)
    return alerta


def listar_andon(db: Session, sucursal_id: int | None = None) -> list[AndonAlerta]:
    q = db.query(AndonAlerta)
    if sucursal_id is not None:
        q = q.filter(AndonAlerta.sucursal_id == sucursal_id)
    return q.order_by(AndonAlerta.id.desc()).all()


def resumen_andon(db: Session, sucursal_id: int | None = None) -> dict:
    alertas = listar_andon(db, sucursal_id)
    tiempos_resp_min = []
    for a in alertas:
        if a.resuelto_en and a.creado_en:
            tiempos_resp_min.append((a.resuelto_en - a.creado_en).total_seconds() / 60)
    activas = sum(1 for a in alertas if a.estado == EstadoAndon.ACTIVA)
    return {
        "total": len(alertas),
        "activas": activas,
        "tiempo_respuesta_promedio_min": (sum(tiempos_resp_min) / len(tiempos_resp_min)) if tiempos_resp_min else None,
    }


# ---------- Heijunka ----------
def registrar_heijunka_plan(
    db: Session, sucursal_id: int, producto_id: int, fecha: datetime, cantidad_planificada: float,
) -> HeijunkaPlan:
    plan = HeijunkaPlan(
        sucursal_id=sucursal_id, producto_id=producto_id, fecha=fecha,
        cantidad_planificada=cantidad_planificada,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def actualizar_heijunka_real(db: Session, plan_id: int, cantidad_real: float) -> HeijunkaPlan:
    plan = db.query(HeijunkaPlan).get(plan_id)
    if plan is None:
        raise ValueError("Plan Heijunka no encontrado")
    plan.cantidad_real = cantidad_real
    db.commit()
    db.refresh(plan)
    return plan


def listar_heijunka(db: Session, sucursal_id: int | None = None) -> list[HeijunkaPlan]:
    q = db.query(HeijunkaPlan)
    if sucursal_id is not None:
        q = q.filter(HeijunkaPlan.sucursal_id == sucursal_id)
    return q.order_by(HeijunkaPlan.fecha.desc()).all()


def resumen_heijunka(db: Session, sucursal_id: int | None = None) -> dict:
    """Nivelación: qué tan parejo es lo planificado día a día (coeficiente de
    variación de la cantidad planificada, igual criterio que el XYZ de kpi_service)
    y cumplimiento real/plan promedio."""
    planes = listar_heijunka(db, sucursal_id)
    planificadas = [float(p.cantidad_planificada) for p in planes]
    cumplimientos = [
        float(p.cantidad_real) / float(p.cantidad_planificada)
        for p in planes
        if p.cantidad_real is not None and float(p.cantidad_planificada) > 0
    ]
    n = len(planificadas)
    promedio = sum(planificadas) / n if n else 0.0
    varianza = sum((x - promedio) ** 2 for x in planificadas) / n if n else 0.0
    cv_nivelacion = (varianza ** 0.5 / promedio) if promedio > 0 else None
    cumplimiento_promedio_pct = (sum(cumplimientos) / len(cumplimientos) * 100) if cumplimientos else None
    return {
        "registros": len(planes),
        "coeficiente_variacion_plan": cv_nivelacion,
        "nivelacion": (
            "Buena nivelación (CV <= 15%)" if cv_nivelacion is not None and cv_nivelacion <= 0.15
            else "Nivelación irregular (CV > 15%)" if cv_nivelacion is not None else "Sin datos suficientes"
        ),
        "cumplimiento_promedio_pct": cumplimiento_promedio_pct,
    }


# ---------- VSM (Value Stream Mapping) ----------
def crear_vsm_paso(
    db: Session, sucursal_id: int, proceso: str, orden: int, nombre_paso: str,
    tiempo_ciclo_min: float, tiempo_espera_min: float = 0, valor_agregado: bool = True,
) -> VsmPaso:
    paso = VsmPaso(
        sucursal_id=sucursal_id, proceso=proceso, orden=orden, nombre_paso=nombre_paso,
        tiempo_ciclo_min=tiempo_ciclo_min, tiempo_espera_min=tiempo_espera_min,
        valor_agregado=valor_agregado,
    )
    db.add(paso)
    db.commit()
    db.refresh(paso)
    return paso


def listar_vsm(db: Session, proceso: str, sucursal_id: int | None = None) -> list[VsmPaso]:
    q = db.query(VsmPaso).filter(VsmPaso.proceso == proceso)
    if sucursal_id is not None:
        q = q.filter(VsmPaso.sucursal_id == sucursal_id)
    return q.order_by(VsmPaso.orden).all()


def resumen_vsm(db: Session, proceso: str, sucursal_id: int | None = None) -> dict:
    pasos = listar_vsm(db, proceso, sucursal_id)
    tiempo_ciclo_total = sum(float(p.tiempo_ciclo_min) for p in pasos)
    tiempo_espera_total = sum(float(p.tiempo_espera_min) for p in pasos)
    tiempo_va = sum(float(p.tiempo_ciclo_min) for p in pasos if p.valor_agregado)
    lead_time_total = tiempo_ciclo_total + tiempo_espera_total
    pct_va = (tiempo_va / lead_time_total * 100) if lead_time_total > 0 else None
    return {
        "proceso": proceso,
        "pasos": [
            {"orden": p.orden, "nombre_paso": p.nombre_paso, "tiempo_ciclo_min": float(p.tiempo_ciclo_min),
             "tiempo_espera_min": float(p.tiempo_espera_min), "valor_agregado": p.valor_agregado}
            for p in pasos
        ],
        "tiempo_ciclo_total_min": tiempo_ciclo_total,
        "tiempo_espera_total_min": tiempo_espera_total,
        "lead_time_total_min": lead_time_total,
        "tiempo_valor_agregado_min": tiempo_va,
        "pct_valor_agregado": pct_va,
    }


def listar_procesos_vsm(db: Session, sucursal_id: int | None = None) -> list[str]:
    q = db.query(VsmPaso.proceso).distinct()
    if sucursal_id is not None:
        q = q.filter(VsmPaso.sucursal_id == sucursal_id)
    return sorted({row[0] for row in q.all()})
