from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_permission, sucursal_scope, verificar_acceso_sucursal
from app.schemas.lean_captura import (
    Auditoria5SCrear,
    AndonCrear,
    HeijunkaActualizarReal,
    HeijunkaCrear,
    JidokaCrear,
    JidokaResolver,
    KaizenAvanzar,
    KaizenCrear,
    SmedCrear,
    VsmPasoCrear,
)
from app.services import lean_captura_service

router = APIRouter(prefix="/api/lean-captura", tags=["Lean: 5S / Kaizen / SMED / Jidoka / Andon / Heijunka / VSM"])


# ---------- 5S ----------
@router.post("/5s", dependencies=[Depends(require_permission("produccion.escribir"))])
def crear_auditoria_5s(
    payload: Auditoria5SCrear, db: Session = Depends(get_db), scope: int | None = Depends(sucursal_scope)
):
    verificar_acceso_sucursal(payload.sucursal_id, scope)
    try:
        return lean_captura_service.registrar_auditoria_5s(
            db, payload.sucursal_id, payload.area, payload.seiri, payload.seiton, payload.seiso,
            payload.seiketsu, payload.shitsuke, payload.observaciones, payload.auditor,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/5s/resumen", dependencies=[Depends(require_permission("inventario.leer"))])
def resumen_5s(db: Session = Depends(get_db), scope: int | None = Depends(sucursal_scope)):
    return lean_captura_service.resumen_5s(db, sucursal_id=scope)


# ---------- Kaizen ----------
@router.post("/kaizen", dependencies=[Depends(require_permission("produccion.escribir"))])
def crear_kaizen(
    payload: KaizenCrear, db: Session = Depends(get_db), scope: int | None = Depends(sucursal_scope)
):
    verificar_acceso_sucursal(payload.sucursal_id, scope)
    return lean_captura_service.crear_kaizen(
        db, payload.sucursal_id, payload.area, payload.titulo, payload.descripcion,
        payload.responsable, payload.ahorro_estimado,
    )


@router.get("/kaizen", dependencies=[Depends(require_permission("inventario.leer"))])
def listar_kaizen(db: Session = Depends(get_db), scope: int | None = Depends(sucursal_scope)):
    return lean_captura_service.listar_kaizen(db, sucursal_id=scope)


@router.get("/kaizen/resumen", dependencies=[Depends(require_permission("inventario.leer"))])
def resumen_kaizen(db: Session = Depends(get_db), scope: int | None = Depends(sucursal_scope)):
    return lean_captura_service.resumen_kaizen(db, sucursal_id=scope)


@router.post("/kaizen/{kaizen_id}/avanzar", dependencies=[Depends(require_permission("produccion.escribir"))])
def avanzar_kaizen(kaizen_id: int, payload: KaizenAvanzar, db: Session = Depends(get_db)):
    try:
        return lean_captura_service.avanzar_kaizen(db, kaizen_id, payload.nuevo_estado)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------- SMED ----------
@router.post("/smed", dependencies=[Depends(require_permission("produccion.escribir"))])
def crear_smed(
    payload: SmedCrear, db: Session = Depends(get_db), scope: int | None = Depends(sucursal_scope)
):
    verificar_acceso_sucursal(payload.sucursal_id, scope)
    return lean_captura_service.registrar_smed(
        db, payload.sucursal_id, payload.proceso, payload.tiempo_setup_antes_min,
        payload.tiempo_setup_despues_min, payload.tiempo_interno_min, payload.tiempo_externo_min,
        payload.responsable,
    )


@router.get("/smed", dependencies=[Depends(require_permission("inventario.leer"))])
def resumen_smed(db: Session = Depends(get_db), scope: int | None = Depends(sucursal_scope)):
    return lean_captura_service.resumen_smed(db, sucursal_id=scope)


# ---------- Jidoka ----------
@router.post("/jidoka", dependencies=[Depends(require_permission("produccion.escribir"))])
def crear_jidoka(
    payload: JidokaCrear, db: Session = Depends(get_db), scope: int | None = Depends(sucursal_scope)
):
    verificar_acceso_sucursal(payload.sucursal_id, scope)
    return lean_captura_service.registrar_jidoka(
        db, payload.sucursal_id, payload.etapa, payload.motivo_paro, payload.op_id, payload.tiempo_paro_min
    )


@router.post("/jidoka/{evento_id}/resolver", dependencies=[Depends(require_permission("produccion.escribir"))])
def resolver_jidoka(evento_id: int, payload: JidokaResolver, db: Session = Depends(get_db)):
    try:
        return lean_captura_service.resolver_jidoka(db, evento_id, payload.accion_correctiva)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/jidoka", dependencies=[Depends(require_permission("inventario.leer"))])
def listar_jidoka(db: Session = Depends(get_db), scope: int | None = Depends(sucursal_scope)):
    return lean_captura_service.listar_jidoka(db, sucursal_id=scope)


@router.get("/jidoka/resumen", dependencies=[Depends(require_permission("inventario.leer"))])
def resumen_jidoka(db: Session = Depends(get_db), scope: int | None = Depends(sucursal_scope)):
    return lean_captura_service.resumen_jidoka(db, sucursal_id=scope)


# ---------- Andon ----------
@router.post("/andon", dependencies=[Depends(require_permission("produccion.escribir"))])
def crear_andon(
    payload: AndonCrear, db: Session = Depends(get_db), scope: int | None = Depends(sucursal_scope)
):
    verificar_acceso_sucursal(payload.sucursal_id, scope)
    return lean_captura_service.crear_andon(db, payload.sucursal_id, payload.etapa, payload.tipo, payload.descripcion)


@router.post("/andon/{alerta_id}/resolver", dependencies=[Depends(require_permission("produccion.escribir"))])
def resolver_andon(alerta_id: int, db: Session = Depends(get_db)):
    try:
        return lean_captura_service.resolver_andon(db, alerta_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/andon", dependencies=[Depends(require_permission("inventario.leer"))])
def listar_andon(db: Session = Depends(get_db), scope: int | None = Depends(sucursal_scope)):
    return lean_captura_service.listar_andon(db, sucursal_id=scope)


@router.get("/andon/resumen", dependencies=[Depends(require_permission("inventario.leer"))])
def resumen_andon(db: Session = Depends(get_db), scope: int | None = Depends(sucursal_scope)):
    return lean_captura_service.resumen_andon(db, sucursal_id=scope)


# ---------- Heijunka ----------
@router.post("/heijunka", dependencies=[Depends(require_permission("produccion.escribir"))])
def crear_heijunka(
    payload: HeijunkaCrear, db: Session = Depends(get_db), scope: int | None = Depends(sucursal_scope)
):
    verificar_acceso_sucursal(payload.sucursal_id, scope)
    return lean_captura_service.registrar_heijunka_plan(
        db, payload.sucursal_id, payload.producto_id, payload.fecha, payload.cantidad_planificada
    )


@router.post("/heijunka/{plan_id}/real", dependencies=[Depends(require_permission("produccion.escribir"))])
def actualizar_heijunka_real(plan_id: int, payload: HeijunkaActualizarReal, db: Session = Depends(get_db)):
    try:
        return lean_captura_service.actualizar_heijunka_real(db, plan_id, payload.cantidad_real)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/heijunka", dependencies=[Depends(require_permission("inventario.leer"))])
def listar_heijunka(db: Session = Depends(get_db), scope: int | None = Depends(sucursal_scope)):
    return lean_captura_service.listar_heijunka(db, sucursal_id=scope)


@router.get("/heijunka/resumen", dependencies=[Depends(require_permission("inventario.leer"))])
def resumen_heijunka(db: Session = Depends(get_db), scope: int | None = Depends(sucursal_scope)):
    return lean_captura_service.resumen_heijunka(db, sucursal_id=scope)


# ---------- VSM ----------
@router.post("/vsm", dependencies=[Depends(require_permission("produccion.escribir"))])
def crear_vsm_paso(
    payload: VsmPasoCrear, db: Session = Depends(get_db), scope: int | None = Depends(sucursal_scope)
):
    verificar_acceso_sucursal(payload.sucursal_id, scope)
    return lean_captura_service.crear_vsm_paso(
        db, payload.sucursal_id, payload.proceso, payload.orden, payload.nombre_paso,
        payload.tiempo_ciclo_min, payload.tiempo_espera_min, payload.valor_agregado,
    )


@router.get("/vsm/procesos", dependencies=[Depends(require_permission("inventario.leer"))])
def listar_procesos_vsm(db: Session = Depends(get_db), scope: int | None = Depends(sucursal_scope)):
    return lean_captura_service.listar_procesos_vsm(db, sucursal_id=scope)


@router.get("/vsm/{proceso}", dependencies=[Depends(require_permission("inventario.leer"))])
def resumen_vsm(proceso: str, db: Session = Depends(get_db), scope: int | None = Depends(sucursal_scope)):
    return lean_captura_service.resumen_vsm(db, proceso, sucursal_id=scope)
