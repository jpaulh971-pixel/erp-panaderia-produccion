from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_permission
from app.schemas.inteligencia import PreguntaIA
from app.services import inteligencia_service

router = APIRouter(prefix="/api/inteligencia", tags=["Centro de Inteligencia Empresarial"])

_DESPACHADOR = {
    "producir_mañana": lambda db, p: inteligencia_service.producir_mañana(db),
    "tienda_vende_mas": lambda db, p: inteligencia_service.tienda_vende_mas(db),
    "tienda_mas_merma": lambda db, p: inteligencia_service.tienda_mas_merma(db),
    "producto_mas_rentable": lambda db, p: inteligencia_service.producto_mas_rentable(db),
    "impacto_falta_insumo": lambda db, p: inteligencia_service.impacto_falta_insumo(db, _requerido(p, "insumo_id")),
    "costo_real_producto": lambda db, p: inteligencia_service.costo_real_producto(db, _requerido(p, "producto_id")),
    "compra_proxima_semana": lambda db, p: inteligencia_service.compra_proxima_semana(db),
    "op_mayor_eficiencia": lambda db, p: inteligencia_service.op_mayor_eficiencia(db),
    "cuello_de_botella": lambda db, p: inteligencia_service.cuello_de_botella_pregunta(db),
    "producto_retirar": lambda db, p: inteligencia_service.producto_retirar(db),
    "ahorro_reduccion_merma": lambda db, p: inteligencia_service.ahorro_reduccion_merma(db, p.porcentaje or 2.0),
}


def _requerido(p: PreguntaIA, campo: str):
    valor = getattr(p, campo)
    if valor is None:
        raise HTTPException(status_code=400, detail=f"La pregunta '{p.codigo}' requiere el parámetro '{campo}'")
    return valor


@router.get("/preguntas", dependencies=[Depends(require_permission("inventario.leer"))])
def listar_preguntas():
    return inteligencia_service.PREGUNTAS_DISPONIBLES


@router.post("/preguntar", dependencies=[Depends(require_permission("inventario.leer"))])
def preguntar(payload: PreguntaIA, db: Session = Depends(get_db)):
    despachador = _DESPACHADOR.get(payload.codigo)
    if despachador is None:
        raise HTTPException(status_code=400, detail=f"Pregunta desconocida: {payload.codigo}")
    try:
        return despachador(db, payload)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
