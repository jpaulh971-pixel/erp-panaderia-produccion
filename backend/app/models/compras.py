import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class EstadoOC(str, enum.Enum):
    SOLICITADA = "SOLICITADA"
    APROBADA = "APROBADA"
    RECIBIDA = "RECIBIDA"
    ANULADA = "ANULADA"


class OrdenCompra(Base):
    __tablename__ = "ordenes_compra"

    id = Column(Integer, primary_key=True)
    codigo = Column(String, unique=True, nullable=False)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=False)
    almacen_id = Column(Integer, ForeignKey("almacenes.id"), nullable=False)
    estado = Column(Enum(EstadoOC), default=EstadoOC.SOLICITADA)
    creado_en = Column(DateTime, server_default=func.now())

    proveedor = relationship("Proveedor")
    almacen = relationship("Almacen")
    items = relationship("OrdenCompraItem", back_populates="orden", cascade="all, delete-orphan")


class OrdenCompraItem(Base):
    __tablename__ = "orden_compra_items"

    id = Column(Integer, primary_key=True)
    orden_id = Column(Integer, ForeignKey("ordenes_compra.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    cantidad = Column(Numeric(14, 4), nullable=False)
    costo_unitario = Column(Numeric(14, 6), nullable=False)

    orden = relationship("OrdenCompra", back_populates="items")
    producto = relationship("Producto")
