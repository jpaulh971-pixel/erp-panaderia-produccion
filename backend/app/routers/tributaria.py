from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_permission, sucursal_scope, verificar_acceso_sucursal
from app.models.tributaria import EstadoDocumentoSunat, TipoDocumentoSunat
from app.schemas.tributaria import DocumentoSunatAnular, DocumentoSunatCrear
from app.services import tributaria_service

router = APIRouter(prefix="/api/tributaria", tags=["Inteligencia Tributaria: control documental SUNAT"])


@router.post("/documentos", dependencies=[Depends(require_permission("ventas.escribir"))])
def emitir_documento(
    payload: DocumentoSunatCrear, db: Session = Depends(get_db), scope: int | None = Depends(sucursal_scope)
):
    verificar_acceso_sucursal(payload.sucursal_id, scope)
    try:
        return tributaria_service.emitir_documento(
            db, payload.sucursal_id, payload.tipo, payload.serie, payload.numero,
            payload.venta_id, payload.despacho_id, payload.monto,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/documentos/{documento_id}/anular", dependencies=[Depends(require_permission("ventas.escribir"))])
def anular_documento(documento_id: int, payload: DocumentoSunatAnular, db: Session = Depends(get_db)):
    try:
        return tributaria_service.anular_documento(db, documento_id, payload.motivo)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/documentos", dependencies=[Depends(require_permission("ventas.leer"))])
def listar_documentos(
    tipo: TipoDocumentoSunat | None = None,
    estado: EstadoDocumentoSunat | None = None,
    db: Session = Depends(get_db),
    scope: int | None = Depends(sucursal_scope),
):
    return tributaria_service.listar_documentos(db, sucursal_id=scope, tipo=tipo, estado=estado)


@router.get("/ventas-sin-documento", dependencies=[Depends(require_permission("ventas.leer"))])
def ventas_sin_documento(db: Session = Depends(get_db), scope: int | None = Depends(sucursal_scope)):
    return tributaria_service.ventas_sin_documento(db, sucursal_id=scope)


@router.get("/reporte-mermas-desmedros", dependencies=[Depends(require_permission("ventas.leer"))])
def reporte_mermas_desmedros(db: Session = Depends(get_db), scope: int | None = Depends(sucursal_scope)):
    return tributaria_service.reporte_mermas_desmedros(db, sucursal_id=scope)
