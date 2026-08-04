from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import relationship

from app.database import Base

usuario_rol = Table(
    "usuario_rol",
    Base.metadata,
    Column("usuario_id", Integer, ForeignKey("usuarios.id"), primary_key=True),
    Column("rol_id", Integer, ForeignKey("roles.id"), primary_key=True),
)

rol_permiso = Table(
    "rol_permiso",
    Base.metadata,
    Column("rol_id", Integer, ForeignKey("roles.id"), primary_key=True),
    Column("permiso_id", Integer, ForeignKey("permisos.id"), primary_key=True),
)


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    nombre_completo = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    activo = Column(Boolean, default=True)
    sucursal_id = Column(Integer, ForeignKey("sucursales.id"), nullable=True)

    roles = relationship("Rol", secondary=usuario_rol, back_populates="usuarios")
    sucursal = relationship("Sucursal")

    def permisos(self) -> set[str]:
        perms: set[str] = set()
        for rol in self.roles:
            for permiso in rol.permisos:
                perms.add(permiso.codigo)
        return perms


class Rol(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    nombre = Column(String, unique=True, nullable=False)

    usuarios = relationship("Usuario", secondary=usuario_rol, back_populates="roles")
    permisos = relationship("Permiso", secondary=rol_permiso, back_populates="roles")


class Permiso(Base):
    __tablename__ = "permisos"

    id = Column(Integer, primary_key=True)
    codigo = Column(String, unique=True, nullable=False)
    descripcion = Column(String, default="")

    roles = relationship("Rol", secondary=rol_permiso, back_populates="permisos")
