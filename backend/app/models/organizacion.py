from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Empresa(Base):
    __tablename__ = "empresas"

    id = Column(Integer, primary_key=True)
    razon_social = Column(String, nullable=False)
    ruc = Column(String, unique=True, nullable=False)

    sucursales = relationship("Sucursal", back_populates="empresa", cascade="all, delete-orphan")


class Sucursal(Base):
    __tablename__ = "sucursales"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    codigo = Column(String, nullable=False)
    nombre = Column(String, nullable=False)
    direccion = Column(String, default="")
    margen_objetivo = Column(String, default="0.12")  # se guarda como string decimal, se castea en servicios

    empresa = relationship("Empresa", back_populates="sucursales")
