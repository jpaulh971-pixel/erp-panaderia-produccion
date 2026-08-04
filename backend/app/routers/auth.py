from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.auth import Usuario
from app.schemas.auth import LoginRequest, TokenResponse
from app.security import crear_access_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.username == payload.username).first()
    if usuario is None or not verify_password(payload.password, usuario.password_hash):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    if not usuario.activo:
        raise HTTPException(status_code=403, detail="Usuario inactivo")
    token = crear_access_token({"sub": usuario.username})
    return TokenResponse(access_token=token, permisos=sorted(usuario.permisos()))


@router.get("/me")
def me(usuario: Usuario = Depends(get_current_user)):
    return {
        "username": usuario.username,
        "nombre_completo": usuario.nombre_completo,
        "sucursal_id": usuario.sucursal_id,
        "permisos": sorted(usuario.permisos()),
    }
