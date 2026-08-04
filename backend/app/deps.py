from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.auth import Usuario
from app.security import decodificar_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> Usuario:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar la credencial",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None:
        raise credentials_exception
    payload = decodificar_token(token)
    if payload is None:
        raise credentials_exception
    username = payload.get("sub")
    if username is None:
        raise credentials_exception
    usuario = db.query(Usuario).filter(Usuario.username == username).first()
    if usuario is None or not usuario.activo:
        raise credentials_exception
    return usuario


def require_permission(codigo: str):
    def _checker(usuario: Usuario = Depends(get_current_user)) -> Usuario:
        if codigo not in usuario.permisos():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No tiene el permiso requerido: {codigo}",
            )
        return usuario

    return _checker


def sucursal_scope(usuario: Usuario = Depends(get_current_user)) -> int | None:
    """Aislamiento por tienda: si el usuario tiene el permiso amplio
    'organizacion.multisucursal' (admin/gerencia) puede ver todas las tiendas
    (retorna None = sin filtro). Cualquier otro usuario solo puede ver su
    propia sucursal (retorna su sucursal_id); si no tiene sucursal asignada,
    no ve ninguna."""
    if "organizacion.multisucursal" in usuario.permisos():
        return None
    return usuario.sucursal_id if usuario.sucursal_id else -1


def verificar_acceso_sucursal(sucursal_id: int, scope: int | None) -> None:
    if scope is not None and sucursal_id != scope:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene acceso a información de otra tienda",
        )
