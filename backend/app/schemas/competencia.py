from pydantic import BaseModel


class PrecioCompetenciaCrear(BaseModel):
    producto_id: int
    competidor: str
    precio: float
    sucursal_id: int | None = None


class SimularPromocion(BaseModel):
    producto_id: int
    descuento_pct: float
