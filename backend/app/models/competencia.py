"""Inteligencia Competitiva: precios observados de la competencia por
producto, usados para el comparativo de precios, la estimación de
elasticidad (con el histórico real de Venta) y el precio recomendado."""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class PrecioCompetencia(Base):
    __tablename__ = "precios_competencia"

    id = Column(Integer, primary_key=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    sucursal_id = Column(Integer, ForeignKey("sucursales.id"), nullable=True)  # null = precio de zona/mercado general
    competidor = Column(String, nullable=False)
    precio = Column(Numeric(14, 4), nullable=False)
    creado_en = Column(DateTime, server_default=func.now())

    producto = relationship("Producto")
    sucursal = relationship("Sucursal")
