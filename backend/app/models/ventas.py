from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Venta(Base):
    """Registro simplificado de venta POS por tienda/producto, usado para calcular rentabilidad real."""

    __tablename__ = "ventas"

    id = Column(Integer, primary_key=True)
    sucursal_id = Column(Integer, ForeignKey("sucursales.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    cantidad_vendida = Column(Numeric(14, 4), nullable=False)
    total_venta = Column(Numeric(14, 4), nullable=False)
    creado_en = Column(DateTime, server_default=func.now())

    sucursal = relationship("Sucursal")
    producto = relationship("Producto")
