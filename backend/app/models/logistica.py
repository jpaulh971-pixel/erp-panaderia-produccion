import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class EstadoDespacho(str, enum.Enum):
    PROGRAMADO = "PROGRAMADO"
    EN_RUTA = "EN_RUTA"
    ENTREGADO = "ENTREGADO"


class Despacho(Base):
    """Despacho de una OP hacia su tienda destino. 1 OP -> 1 despacho."""

    __tablename__ = "despachos"

    id = Column(Integer, primary_key=True)
    op_id = Column(Integer, ForeignKey("ordenes_produccion.id"), nullable=False, unique=True)
    sucursal_id = Column(Integer, ForeignKey("sucursales.id"), nullable=False)
    responsable = Column(String, nullable=False)
    vehiculo = Column(String, default="")
    hora_salida = Column(DateTime, server_default=func.now())
    estado = Column(Enum(EstadoDespacho), default=EstadoDespacho.PROGRAMADO)
    creado_en = Column(DateTime, server_default=func.now())

    op = relationship("OrdenProduccion")
    sucursal = relationship("Sucursal")
    recepcion = relationship("RecepcionTienda", back_populates="despacho", uselist=False)


class RecepcionTienda(Base):
    """Recepción en tienda de un despacho: cantidad aceptada, merma de transporte, observaciones."""

    __tablename__ = "recepciones_tienda"

    id = Column(Integer, primary_key=True)
    despacho_id = Column(Integer, ForeignKey("despachos.id"), nullable=False, unique=True)
    cantidad_recepcionada = Column(Numeric(14, 4), nullable=False)
    cantidad_merma = Column(Numeric(14, 4), nullable=False, default=0)
    aceptado = Column(Integer, default=1)  # 1 = aceptado, 0 = rechazado
    observaciones = Column(String, default="")
    creado_en = Column(DateTime, server_default=func.now())

    despacho = relationship("Despacho", back_populates="recepcion")
