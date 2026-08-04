from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_permission
from app.models.productos import Producto, Proveedor
from app.schemas.productos import ProductoCrear, ProductoOut, ProveedorCrear, ProveedorOut

router = APIRouter(prefix="/api/productos", tags=["Maestros"])


@router.post("", response_model=ProductoOut, dependencies=[Depends(require_permission("productos.escribir"))])
def crear_producto(payload: ProductoCrear, db: Session = Depends(get_db)):
    if db.query(Producto).filter(Producto.codigo == payload.codigo).first():
        raise HTTPException(status_code=400, detail="Ya existe un producto con ese código")
    producto = Producto(**payload.model_dump())
    db.add(producto)
    db.commit()
    db.refresh(producto)
    return producto


@router.get("", response_model=list[ProductoOut])
def listar_productos(db: Session = Depends(get_db)):
    return db.query(Producto).all()


@router.post(
    "/proveedores", response_model=ProveedorOut, dependencies=[Depends(require_permission("productos.escribir"))]
)
def crear_proveedor(payload: ProveedorCrear, db: Session = Depends(get_db)):
    proveedor = Proveedor(**payload.model_dump())
    db.add(proveedor)
    db.commit()
    db.refresh(proveedor)
    return proveedor


@router.get("/proveedores", response_model=list[ProveedorOut])
def listar_proveedores(db: Session = Depends(get_db)):
    return db.query(Proveedor).all()
