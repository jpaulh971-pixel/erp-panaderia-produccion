import enum

from sqlalchemy import Column, Enum, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class TipoProducto(str, enum.Enum):
    INSUMO = "INSUMO"
    SEMIELABORADO = "SEMIELABORADO"
    TERMINADO = "TERMINADO"
    MERCADERIA = "MERCADERIA"


class Producto(Base):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True)
    codigo = Column(String, unique=True, nullable=False)
    nombre = Column(String, nullable=False)
    unidad = Column(String, nullable=False, default="unidad")
    tipo = Column(Enum(TipoProducto), nullable=False, default=TipoProducto.INSUMO)

    lotes = relationship("LoteInventario", back_populates="producto")


class Proveedor(Base):
    __tablename__ = "proveedores"

    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    ruc = Column(String, default="")
    contacto = Column(String, default="")


class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    documento = Column(String, default="")
