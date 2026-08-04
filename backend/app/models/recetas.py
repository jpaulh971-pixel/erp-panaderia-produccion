from sqlalchemy import Boolean, Column, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import DateTime

from app.database import Base


class RecetaVersion(Base):
    __tablename__ = "receta_versiones"

    id = Column(Integer, primary_key=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    rendimiento_unidades = Column(Numeric(14, 4), nullable=False, default=1)
    merma_estimada_pct = Column(Numeric(6, 4), nullable=False, default=0)
    activa = Column(Boolean, default=True)
    creado_en = Column(DateTime, server_default=func.now())

    producto = relationship("Producto")
    ingredientes = relationship(
        "RecetaIngrediente", back_populates="receta", cascade="all, delete-orphan"
    )


class RecetaIngrediente(Base):
    __tablename__ = "receta_ingredientes"

    id = Column(Integer, primary_key=True)
    receta_id = Column(Integer, ForeignKey("receta_versiones.id"), nullable=False)
    insumo_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    cantidad_por_unidad = Column(Numeric(14, 6), nullable=False)

    receta = relationship("RecetaVersion", back_populates="ingredientes")
    insumo = relationship("Producto")
