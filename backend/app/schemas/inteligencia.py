from pydantic import BaseModel


class PreguntaIA(BaseModel):
    codigo: str
    insumo_id: int | None = None
    producto_id: int | None = None
    porcentaje: float | None = None
