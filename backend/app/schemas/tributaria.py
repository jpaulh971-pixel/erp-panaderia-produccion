from pydantic import BaseModel

from app.models.tributaria import TipoDocumentoSunat


class DocumentoSunatCrear(BaseModel):
    sucursal_id: int
    tipo: TipoDocumentoSunat
    serie: str
    numero: str
    venta_id: int | None = None
    despacho_id: int | None = None
    monto: float | None = None


class DocumentoSunatAnular(BaseModel):
    motivo: str = ""
