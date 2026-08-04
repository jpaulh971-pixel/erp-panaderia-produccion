from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_permission
from app.schemas.recetas import RecetaCrear, RecetaOut
from app.services import recetas_service

router = APIRouter(prefix="/api/recetas", tags=["Recetas"])


@router.post("", response_model=RecetaOut, dependencies=[Depends(require_permission("recetas.escribir"))])
def crear_receta(payload: RecetaCrear, db: Session = Depends(get_db)):
    receta = recetas_service.crear_version_receta(
        db, payload.producto_id, payload.rendimiento_unidades,
        [i.model_dump() for i in payload.ingredientes], payload.merma_estimada_pct,
    )
    return receta


@router.get("/producto/{producto_id}/activa", response_model=RecetaOut)
def obtener_receta_activa(producto_id: int, db: Session = Depends(get_db)):
    receta = recetas_service.receta_activa(db, producto_id)
    if receta is None:
        raise HTTPException(status_code=404, detail="El producto no tiene receta activa")
    return receta


@router.get("/producto/{producto_id}/costo-estandar")
def costo_estandar(producto_id: int, almacen_id: int, db: Session = Depends(get_db)):
    try:
        registro = recetas_service.calcular_costo_estandar(db, producto_id, almacen_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"producto_id": producto_id, "costo_unitario": float(registro.costo_unitario)}
