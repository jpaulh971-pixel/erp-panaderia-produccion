import enum

from sqlalchemy import Column, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class TipoMovimiento(str, enum.Enum):
    INGRESO_COMPRA = "INGRESO_COMPRA"
    INGRESO_PRODUCCION = "INGRESO_PRODUCCION"
    SALIDA_CONSUMO = "SALIDA_CONSUMO"
    SALIDA_MERMA = "SALIDA_MERMA"
    SALIDA_VENTA = "SALIDA_VENTA"


class Almacen(Base):
    __tablename__ = "almacenes"

    id = Column(Integer, primary_key=True)
    sucursal_id = Column(Integer, ForeignKey("sucursales.id"), nullable=False, unique=True)
    nombre = Column(String, default="Almacén principal")

    sucursal = relationship("Sucursal")
    lotes = relationship("LoteInventario", back_populates="almacen")


class LoteInventario(Base):
    """Un lote de stock disponible para un producto en un almacén (soporte FIFO/FEFO)."""

    __tablename__ = "lotes_inventario"

    id = Column(Integer, primary_key=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    almacen_id = Column(Integer, ForeignKey("almacenes.id"), nullable=False)
    codigo_lote = Column(String, nullable=False)
    cantidad_disponible = Column(Numeric(14, 4), nullable=False, default=0)
    costo_unitario = Column(Numeric(14, 6), nullable=False, default=0)
    fecha_ingreso = Column(DateTime, server_default=func.now())
    fecha_vencimiento = Column(Date, nullable=True)
    referencia = Column(String, default="")

    producto = relationship("Producto", back_populates="lotes")
    almacen = relationship("Almacen", back_populates="lotes")


class MovimientoInventario(Base):
    """Kardex: registro histórico de todos los movimientos de inventario."""

    __tablename__ = "movimientos_inventario"

    id = Column(Integer, primary_key=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    almacen_id = Column(Integer, ForeignKey("almacenes.id"), nullable=False)
    tipo = Column(Enum(TipoMovimiento), nullable=False)
    cantidad = Column(Numeric(14, 4), nullable=False)
    costo_unitario = Column(Numeric(14, 6), nullable=False, default=0)
    costo_total = Column(Numeric(14, 6), nullable=False, default=0)
    referencia = Column(String, default="")
    creado_en = Column(DateTime, server_default=func.now())

    producto = relationship("Producto")
    almacen = relationship("Almacen")
