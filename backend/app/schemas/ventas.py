from pydantic import BaseModel


class VentaCrear(BaseModel):
    sucursal_id: int
    producto_id: int
    cantidad_vendida: float
    total_venta: float
