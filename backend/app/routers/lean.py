from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_permission
from app.services import lean_service

router = APIRouter(prefix="/api/lean", tags=["Lean / Six Sigma / TOC"])


@router.get("/cuello-de-botella", dependencies=[Depends(require_permission("inventario.leer"))])
def cuello_de_botella(db: Session = Depends(get_db)):
    return lean_service.cuello_de_botella(db)


@router.get("/oee", dependencies=[Depends(require_permission("inventario.leer"))])
def oee(db: Session = Depends(get_db)):
    return lean_service.oee_aproximado(db)


@router.get("/capacidad-proceso", dependencies=[Depends(require_permission("inventario.leer"))])
def capacidad_proceso(tolerancia_pct: float = 0.10, db: Session = Depends(get_db)):
    return lean_service.capacidad_proceso(db, tolerancia_pct)


@router.get("/kanban", dependencies=[Depends(require_permission("inventario.leer"))])
def kanban(db: Session = Depends(get_db)):
    return lean_service.tablero_kanban(db)
