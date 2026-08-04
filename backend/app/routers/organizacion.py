from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_permission
from app.models.organizacion import Empresa, Sucursal

router = APIRouter(prefix="/api/organizacion", tags=["Organización"])


@router.get("/empresas", dependencies=[Depends(require_permission("organizacion.leer"))])
def listar_empresas(db: Session = Depends(get_db)):
    return db.query(Empresa).all()


@router.get("/sucursales", dependencies=[Depends(require_permission("organizacion.leer"))])
def listar_sucursales(db: Session = Depends(get_db)):
    return [
        {"id": s.id, "codigo": s.codigo, "nombre": s.nombre, "empresa_id": s.empresa_id}
        for s in db.query(Sucursal).all()
    ]
