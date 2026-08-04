"""Módulos Lean que son checklists/tableros de captura operativa (no cálculo
puro como OEE/Cp-Cpk/TOC, que ya viven en app/services/lean_service.py):
5S, Kaizen, SMED, Jidoka, Andon, Heijunka y Value Stream Mapping.

Cada modelo captura el dato real que el equipo de planta registra en el día
a día; los indicadores (puntaje 5S, % mejora SMED, tiempo de respuesta Andon,
cumplimiento Heijunka, %VA del VSM) se calculan en lean_captura_service.py
a partir de estos registros, nunca se inventan.
"""
import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class EstadoKaizen(str, enum.Enum):
    PROPUESTA = "PROPUESTA"
    EN_CURSO = "EN_CURSO"
    IMPLEMENTADA = "IMPLEMENTADA"
    DESCARTADA = "DESCARTADA"


class TipoAndon(str, enum.Enum):
    CALIDAD = "CALIDAD"
    MATERIAL = "MATERIAL"
    MANTENIMIENTO = "MANTENIMIENTO"
    SEGURIDAD = "SEGURIDAD"


class EstadoAndon(str, enum.Enum):
    ACTIVA = "ACTIVA"
    RESUELTA = "RESUELTA"


class Auditoria5S(Base):
    """Auditoría 5S por área/sucursal: puntaje 0-5 en cada una de las 5 eses."""

    __tablename__ = "auditorias_5s"

    id = Column(Integer, primary_key=True)
    sucursal_id = Column(Integer, ForeignKey("sucursales.id"), nullable=False)
    area = Column(String, nullable=False)
    seiri = Column(Integer, nullable=False)  # Clasificar
    seiton = Column(Integer, nullable=False)  # Ordenar
    seiso = Column(Integer, nullable=False)  # Limpiar
    seiketsu = Column(Integer, nullable=False)  # Estandarizar
    shitsuke = Column(Integer, nullable=False)  # Disciplina
    observaciones = Column(String, default="")
    auditor = Column(String, default="")
    creado_en = Column(DateTime, server_default=func.now())

    sucursal = relationship("Sucursal")


class KaizenPropuesta(Base):
    """Propuesta de mejora continua: de idea a resultado medible."""

    __tablename__ = "kaizen_propuestas"

    id = Column(Integer, primary_key=True)
    sucursal_id = Column(Integer, ForeignKey("sucursales.id"), nullable=False)
    area = Column(String, nullable=False)
    titulo = Column(String, nullable=False)
    descripcion = Column(String, default="")
    responsable = Column(String, default="")
    estado = Column(Enum(EstadoKaizen), nullable=False, default=EstadoKaizen.PROPUESTA)
    ahorro_estimado = Column(Numeric(14, 2), nullable=True)
    creado_en = Column(DateTime, server_default=func.now())
    actualizado_en = Column(DateTime, server_default=func.now(), onupdate=func.now())

    sucursal = relationship("Sucursal")


class SmedRegistro(Base):
    """Cambio de formato/setup: tiempo antes vs. después de aplicar SMED
    (separar actividades internas de externas, convertir internas en externas)."""

    __tablename__ = "smed_registros"

    id = Column(Integer, primary_key=True)
    sucursal_id = Column(Integer, ForeignKey("sucursales.id"), nullable=False)
    proceso = Column(String, nullable=False)  # ej. "cambio de molde horno 2"
    tiempo_setup_antes_min = Column(Numeric(10, 2), nullable=False)
    tiempo_setup_despues_min = Column(Numeric(10, 2), nullable=True)
    tiempo_interno_min = Column(Numeric(10, 2), nullable=True)  # con máquina parada
    tiempo_externo_min = Column(Numeric(10, 2), nullable=True)  # con máquina en marcha
    responsable = Column(String, default="")
    creado_en = Column(DateTime, server_default=func.now())

    sucursal = relationship("Sucursal")


class JidokaEvento(Base):
    """Paro automático/manual de línea por defecto detectado (autonomatización:
    la línea se detiene sola en vez de producir defectos en serie)."""

    __tablename__ = "jidoka_eventos"

    id = Column(Integer, primary_key=True)
    sucursal_id = Column(Integer, ForeignKey("sucursales.id"), nullable=False)
    op_id = Column(Integer, ForeignKey("ordenes_produccion.id"), nullable=True)
    etapa = Column(String, nullable=False)
    motivo_paro = Column(String, nullable=False)
    tiempo_paro_min = Column(Numeric(10, 2), nullable=True)
    resuelto = Column(Boolean, nullable=False, default=False)
    accion_correctiva = Column(String, default="")
    creado_en = Column(DateTime, server_default=func.now())
    resuelto_en = Column(DateTime, nullable=True)

    sucursal = relationship("Sucursal")
    op = relationship("OrdenProduccion")


class AndonAlerta(Base):
    """Alerta visual de línea (calidad/material/mantenimiento/seguridad):
    tiempo de respuesta = resuelto_en - creado_en."""

    __tablename__ = "andon_alertas"

    id = Column(Integer, primary_key=True)
    sucursal_id = Column(Integer, ForeignKey("sucursales.id"), nullable=False)
    etapa = Column(String, nullable=False)
    tipo = Column(Enum(TipoAndon), nullable=False)
    descripcion = Column(String, default="")
    estado = Column(Enum(EstadoAndon), nullable=False, default=EstadoAndon.ACTIVA)
    creado_en = Column(DateTime, server_default=func.now())
    resuelto_en = Column(DateTime, nullable=True)

    sucursal = relationship("Sucursal")


class HeijunkaPlan(Base):
    """Nivelación de producción: cantidad planificada vs. real por producto/día,
    para medir qué tan pareja (heijunka) es la carga real frente al plan."""

    __tablename__ = "heijunka_plan"

    id = Column(Integer, primary_key=True)
    sucursal_id = Column(Integer, ForeignKey("sucursales.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    fecha = Column(DateTime, nullable=False)
    cantidad_planificada = Column(Numeric(14, 4), nullable=False)
    cantidad_real = Column(Numeric(14, 4), nullable=True)
    creado_en = Column(DateTime, server_default=func.now())

    sucursal = relationship("Sucursal")
    producto = relationship("Producto")


class VsmPaso(Base):
    """Un paso del Value Stream Mapping de un proceso: tiempo de ciclo, tiempo
    de espera hasta el siguiente paso, y si agrega valor o no."""

    __tablename__ = "vsm_pasos"

    id = Column(Integer, primary_key=True)
    sucursal_id = Column(Integer, ForeignKey("sucursales.id"), nullable=False)
    proceso = Column(String, nullable=False)  # nombre del flujo mapeado, ej. "Torta de Chocolate"
    orden = Column(Integer, nullable=False)
    nombre_paso = Column(String, nullable=False)
    tiempo_ciclo_min = Column(Numeric(10, 2), nullable=False, default=0)
    tiempo_espera_min = Column(Numeric(10, 2), nullable=False, default=0)
    valor_agregado = Column(Boolean, nullable=False, default=True)
    creado_en = Column(DateTime, server_default=func.now())

    sucursal = relationship("Sucursal")
