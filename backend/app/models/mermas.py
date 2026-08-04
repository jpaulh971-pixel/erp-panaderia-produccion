import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class TipoPerdida(str, enum.Enum):
    """Distinción que exige SUNAT: la merma es deducible sin trámite adicional
    si está acreditada; el desmedro requiere destrucción con acta notarial o
    comunicación previa a SUNAT para ser deducible."""

    MERMA = "MERMA"
    DESMEDRO = "DESMEDRO"


class Merma(Base):
    __tablename__ = "mermas"

    id = Column(Integer, primary_key=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    almacen_id = Column(Integer, ForeignKey("almacenes.id"), nullable=False)
    cantidad = Column(Numeric(14, 4), nullable=False)
    motivo = Column(String, default="")
    tipo_perdida = Column(Enum(TipoPerdida), nullable=False, default=TipoPerdida.MERMA)
    costo_valorizado = Column(Numeric(14, 6), nullable=False, default=0)
    creado_en = Column(DateTime, server_default=func.now())

    producto = relationship("Producto")
    almacen = relationship("Almacen")
