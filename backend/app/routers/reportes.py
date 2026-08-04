from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_permission
from app.services import reportes_service

router = APIRouter(prefix="/api/reportes", tags=["Reportes"])


@router.get("/dosificacion/{op_id}.pdf", dependencies=[Depends(require_permission("produccion.escribir"))])
def hoja_dosificacion(op_id: int, db: Session = Depends(get_db)):
    try:
        contenido = reportes_service.hoja_dosificacion_pdf(db, op_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return Response(
        content=contenido,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=dosificacion_op_{op_id}.pdf"},
    )


@router.get("/produccion.xlsx", dependencies=[Depends(require_permission("inventario.leer"))])
def exportar_produccion(db: Session = Depends(get_db)):
    contenido = reportes_service.exportar_produccion_excel(db)
    return Response(
        content=contenido,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=produccion.xlsx"},
    )


@router.get("/kardex.xlsx", dependencies=[Depends(require_permission("inventario.leer"))])
def exportar_kardex(db: Session = Depends(get_db)):
    contenido = reportes_service.exportar_kardex_excel(db)
    return Response(
        content=contenido,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=kardex.xlsx"},
    )
