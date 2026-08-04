import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class EstadoOP(str, enum.Enum):
    SOLICITADA = "SOLICITADA"
    APROBADA = "APROBADA"
    DOSIFICACION = "DOSIFICACION"
    PRODUCCION = "PRODUCCION"
    HORNEADO = "HORNEADO"
    EMPAQUE = "EMPAQUE"
    DESPACHO = "DESPACHO"
    RECEPCION = "RECEPCION"
    FACTURADO = "FACTURADO"


# Máquina de estados lineal: cada estado sólo puede avanzar al siguiente.
SIGUIENTE_ESTADO = {
    EstadoOP.SOLICITADA: EstadoOP.APROBADA,
    EstadoOP.APROBADA: EstadoOP.DOSIFICACION,
    EstadoOP.DOSIFICACION: EstadoOP.PRODUCCION,
    EstadoOP.PRODUCCION: EstadoOP.HORNEADO,
    EstadoOP.HORNEADO: EstadoOP.EMPAQUE,
    EstadoOP.EMPAQUE: EstadoOP.DESPACHO,
    EstadoOP.DESPACHO: EstadoOP.RECEPCION,
    EstadoOP.RECEPCION: EstadoOP.FACTURADO,
    EstadoOP.FACTURADO: None,
}


class OrdenProduccion(Base):
    __tablename__ = "ordenes_produccion"

    id = Column(Integer, primary_key=True)
    codigo = Column(String, unique=True, nullable=False)
    sucursal_id = Column(Integer, ForeignKey("sucursales.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    cantidad_solicitada = Column(Numeric(14, 4), nullable=False)
    cantidad_producida = Column(Numeric(14, 4), nullable=True)
    estado = Column(Enum(EstadoOP), default=EstadoOP.SOLICITADA)
    costo_insumos_real = Column(Numeric(14, 6), nullable=True)
    costo_real_total = Column(Numeric(14, 6), nullable=True)
    creado_en = Column(DateTime, server_default=func.now())

    sucursal = relationship("Sucursal")
    producto = relationship("Producto")
    historial = relationship(
        "HistorialEstadoOP", back_populates="op", cascade="all, delete-orphan",
        order_by="HistorialEstadoOP.id",
    )


class HistorialEstadoOP(Base):
    """Traza cada transición de estado de una OP con su timestamp real.
    Es la base de datos para Lean/TOC: tiempo de ciclo por etapa, cuello de
    botella y OEE (Availability), calculados sobre tiempos reales, no estimados."""

    __tablename__ = "historial_estado_op"

    id = Column(Integer, primary_key=True)
    op_id = Column(Integer, ForeignKey("ordenes_produccion.id"), nullable=False)
    estado = Column(Enum(EstadoOP), nullable=False)
    creado_en = Column(DateTime, server_default=func.now())

    op = relationship("OrdenProduccion", back_populates="historial")
