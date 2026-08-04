from pydantic import BaseModel

from app.models.mermas import TipoPerdida


class MermaCrear(BaseModel):
    producto_id: int
    sucursal_id: int
    cantidad: float
    motivo: str = ""
    tipo_perdida: TipoPerdida = TipoPerdida.MERMA
