from datetime import datetime

from pydantic import BaseModel


class DespachoCrear(BaseModel):
    op_id: int
    responsable: str
    vehiculo: str = ""


class DespachoOut(BaseModel):
    id: int
    op_id: int
    sucursal_id: int
    responsable: str
    vehiculo: str
    estado: str
    hora_salida: datetime | None = None

    model_config = {"from_attributes": True}


class RecepcionCrear(BaseModel):
    despacho_id: int
    cantidad_recepcionada: float
    cantidad_merma: float = 0
    aceptado: bool = True
    observaciones: str = ""


class RecepcionOut(BaseModel):
    id: int
    despacho_id: int
    cantidad_recepcionada: float
    cantidad_merma: float
    aceptado: int
    observaciones: str

    model_config = {"from_attributes": True}
