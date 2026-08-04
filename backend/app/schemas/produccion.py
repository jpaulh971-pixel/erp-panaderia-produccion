from pydantic import BaseModel


class OPCrear(BaseModel):
    sucursal_id: int
    producto_id: int
    cantidad_solicitada: float


class OPAvanzar(BaseModel):
    nuevo_estado: str
    cantidad_producida: float | None = None


class OPOut(BaseModel):
    id: int
    codigo: str
    estado: str
    sucursal_id: int
    producto_id: int
    cantidad_solicitada: float
    cantidad_producida: float | None = None
    costo_insumos_real: float | None = None
    costo_real_total: float | None = None

    class Config:
        from_attributes = True
