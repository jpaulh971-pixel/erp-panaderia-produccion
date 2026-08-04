from pydantic import BaseModel

from app.models.compras import EstadoOC


class OrdenCompraItemIn(BaseModel):
    producto_id: int
    cantidad: float
    costo_unitario: float


class OrdenCompraCrear(BaseModel):
    proveedor_id: int
    sucursal_id: int
    items: list[OrdenCompraItemIn]


class OrdenCompraOut(BaseModel):
    id: int
    codigo: str
    estado: EstadoOC
    proveedor_id: int
    almacen_id: int

    class Config:
        from_attributes = True
