from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_permission, sucursal_scope, verificar_acceso_sucursal
from app.schemas.calidad import CpCpkRequest, MedicionSPCCrear
from app.services import spc_service

router = APIRouter(prefix="/api/calidad", tags=["Six Sigma: SPC / Control Charts"])


@router.post("/mediciones", dependencies=[Depends(require_permission("produccion.escribir"))])
def registrar_medicion(
    payload: MedicionSPCCrear, db: Session = Depends(get_db), scope: int | None = Depends(sucursal_scope)
):
    verificar_acceso_sucursal(payload.sucursal_id, scope)
    return spc_service.registrar_medicion(
        db, payload.sucursal_id, payload.variable, payload.valor, payload.producto_id, payload.lote
    )


@router.get("/variables", dependencies=[Depends(require_permission("inventario.leer"))])
def variables_disponibles(db: Session = Depends(get_db), scope: int | None = Depends(sucursal_scope)):
    return spc_service.variables_disponibles(db, sucursal_id=scope)


@router.get("/control-chart/{variable}", dependencies=[Depends(require_permission("inventario.leer"))])
def carta_control(variable: str, db: Session = Depends(get_db), scope: int | None = Depends(sucursal_scope)):
    return spc_service.carta_control_imr(db, variable, sucursal_id=scope)


@router.get("/histograma/{variable}", dependencies=[Depends(require_permission("inventario.leer"))])
def histograma(
    variable: str, bins: int = 10, db: Session = Depends(get_db), scope: int | None = Depends(sucursal_scope)
):
    return spc_service.histograma(db, variable, sucursal_id=scope, bins=bins)


@router.post("/cp-cpk/{variable}", dependencies=[Depends(require_permission("inventario.leer"))])
def cp_cpk(
    variable: str, payload: CpCpkRequest, db: Session = Depends(get_db),
    scope: int | None = Depends(sucursal_scope),
):
    return spc_service.cp_cpk(db, variable, payload.lsl, payload.usl, sucursal_id=scope)
