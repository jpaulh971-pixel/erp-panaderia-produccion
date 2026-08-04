"""Inteligencia Tributaria: control documental (facturas, boletas, guías de
remisión) enlazado a las ventas y despachos reales que ya registra el ERP,
y clasificación merma/desmedro para el reporte que se presenta a SUNAT.

No se modela la conexión real a SUNAT (facturación electrónica, SIRE, etc.):
eso requiere un proveedor de facturación electrónica externo (PSE/OSE) que
este ERP todavía no integra. Lo que sí es real es el control documental
interno: qué documento respalda cada venta/despacho, su estado, y el
reporte consolidado de mermas vs. desmedros que ese control alimenta.
"""
import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class TipoDocumentoSunat(str, enum.Enum):
    FACTURA = "FACTURA"
    BOLETA = "BOLETA"
    GUIA_REMISION = "GUIA_REMISION"
    NOTA_CREDITO = "NOTA_CREDITO"


class EstadoDocumentoSunat(str, enum.Enum):
    EMITIDO = "EMITIDO"
    ANULADO = "ANULADO"


class DocumentoSunat(Base):
    __tablename__ = "documentos_sunat"

    id = Column(Integer, primary_key=True)
    sucursal_id = Column(Integer, ForeignKey("sucursales.id"), nullable=False)
    tipo = Column(Enum(TipoDocumentoSunat), nullable=False)
    serie = Column(String, nullable=False)
    numero = Column(String, nullable=False)
    venta_id = Column(Integer, ForeignKey("ventas.id"), nullable=True)
    despacho_id = Column(Integer, ForeignKey("despachos.id"), nullable=True)
    monto = Column(Numeric(14, 4), nullable=True)
    estado = Column(Enum(EstadoDocumentoSunat), nullable=False, default=EstadoDocumentoSunat.EMITIDO)
    motivo_anulacion = Column(String, default="")
    creado_en = Column(DateTime, server_default=func.now())
    anulado_en = Column(DateTime, nullable=True)

    sucursal = relationship("Sucursal")
    venta = relationship("Venta")
    despacho = relationship("Despacho")
