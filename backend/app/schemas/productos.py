from pydantic import BaseModel, ConfigDict

from app.models.productos import TipoProducto


class ProductoCrear(BaseModel):
    codigo: str
    nombre: str
    unidad: str = "unidad"
    tipo: TipoProducto = TipoProducto.INSUMO


class ProductoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    codigo: str
    nombre: str
    unidad: str
    tipo: TipoProducto


class ProveedorCrear(BaseModel):
    nombre: str
    ruc: str = ""
    contacto: str = ""


class ProveedorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    ruc: str
    contacto: str
