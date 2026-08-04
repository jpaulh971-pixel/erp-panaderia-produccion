"""Captura de mediciones de calidad para SPC (Statistical Process Control):
cartas de control (Individuales-Rango Móvil) e histogramas sobre variables
reales medidas en planta (peso, temperatura, humedad, brix, etc.)."""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class MedicionSPC(Base):
    __tablename__ = "mediciones_spc"

    id = Column(Integer, primary_key=True)
    sucursal_id = Column(Integer, ForeignKey("sucursales.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=True)
    variable = Column(String, nullable=False)  # ej. "peso_torta_kg", "temp_horno_c"
    valor = Column(Numeric(14, 6), nullable=False)
    lote = Column(String, default="")
    creado_en = Column(DateTime, server_default=func.now())

    sucursal = relationship("Sucursal")
    producto = relationship("Producto")
