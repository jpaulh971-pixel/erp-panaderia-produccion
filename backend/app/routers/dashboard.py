from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_permission, sucursal_scope
from app.services import kpi_service

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard Ejecutivo"])


@router.get("/resumen", dependencies=[Depends(require_permission("inventario.leer"))])
def resumen(db: Session = Depends(get_db), scope: int | None = Depends(sucursal_scope)):
    return kpi_service.resumen_ejecutivo(db, sucursal_id=scope)


@router.get("/pareto-productos", dependencies=[Depends(require_permission("inventario.leer"))])
def pareto_productos(db: Session = Depends(get_db), scope: int | None = Depends(sucursal_scope)):
    return kpi_service.pareto_productos(db, sucursal_id=scope)


@router.get("/xyz-productos", dependencies=[Depends(require_permission("inventario.leer"))])
def xyz_productos(dias: int = 30, db: Session = Depends(get_db), scope: int | None = Depends(sucursal_scope)):
    return kpi_service.xyz_productos(db, dias=dias, sucursal_id=scope)


@router.get("/ranking-tiendas/{producto_id}", dependencies=[Depends(require_permission("inventario.leer"))])
def ranking_tiendas_por_producto(
    producto_id: int, db: Session = Depends(get_db), scope: int | None = Depends(sucursal_scope)
):
    # Este ranking compara tiendas entre sí: solo tiene sentido (y solo se
    # expone) para usuarios con visión multisucursal (admin/gerencia).
    if scope is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este ranking compara todas las tiendas; requiere acceso multisucursal",
        )
    return kpi_service.ranking_tiendas_por_producto(db, producto_id)
