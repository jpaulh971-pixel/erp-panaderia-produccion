from pydantic import BaseModel


class MedicionSPCCrear(BaseModel):
    sucursal_id: int
    variable: str
    valor: float
    producto_id: int | None = None
    lote: str = ""


class CpCpkRequest(BaseModel):
    lsl: float
    usl: float
