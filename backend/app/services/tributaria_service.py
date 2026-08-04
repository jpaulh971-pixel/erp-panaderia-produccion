"""Inteligencia Tributaria: control documental interno enlazado a ventas y
despachos reales, más el reporte que separa MERMA de DESMEDRO (distinción
que exige SUNAT: la merma es deducible sin trámite adicional si está
acreditada; el desmedro requiere destrucción con acta notarial o
comunicación previa a SUNAT para ser deducible)."""
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.logistica import Despacho
from app.models.mermas import Merma, TipoPerdida
from app.models.tributaria import DocumentoSunat, EstadoDocumentoSunat, TipoDocumentoSunat
from app.models.ventas import Venta


def emitir_documento(
    db: Session, sucursal_id: int, tipo: TipoDocumentoSunat, serie: str, numero: str,
    venta_id: int | None = None, despacho_id: int | None = None, monto: float | None = None,
) -> DocumentoSunat:
    if venta_id is not None and db.query(Venta).get(venta_id) is None:
        raise ValueError("La venta indicada no existe")
    if despacho_id is not None and db.query(Despacho).get(despacho_id) is None:
        raise ValueError("El despacho indicado no existe")
    existente = (
        db.query(DocumentoSunat)
        .filter(DocumentoSunat.tipo == tipo, DocumentoSunat.serie == serie, DocumentoSunat.numero == numero)
        .first()
    )
    if existente is not None:
        raise ValueError(f"Ya existe un documento {tipo.value} {serie}-{numero}")
    documento = DocumentoSunat(
        sucursal_id=sucursal_id, tipo=tipo, serie=serie, numero=numero,
        venta_id=venta_id, despacho_id=despacho_id, monto=monto,
    )
    db.add(documento)
    db.commit()
    db.refresh(documento)
    return documento


def anular_documento(db: Session, documento_id: int, motivo: str = "") -> DocumentoSunat:
    documento = db.query(DocumentoSunat).get(documento_id)
    if documento is None:
        raise ValueError("Documento no encontrado")
    if documento.estado == EstadoDocumentoSunat.ANULADO:
        raise ValueError("El documento ya está anulado")
    documento.estado = EstadoDocumentoSunat.ANULADO
    documento.motivo_anulacion = motivo
    documento.anulado_en = datetime.utcnow()
    db.commit()
    db.refresh(documento)
    return documento


def listar_documentos(
    db: Session, sucursal_id: int | None = None, tipo: TipoDocumentoSunat | None = None,
    estado: EstadoDocumentoSunat | None = None,
) -> list[DocumentoSunat]:
    q = db.query(DocumentoSunat)
    if sucursal_id is not None:
        q = q.filter(DocumentoSunat.sucursal_id == sucursal_id)
    if tipo is not None:
        q = q.filter(DocumentoSunat.tipo == tipo)
    if estado is not None:
        q = q.filter(DocumentoSunat.estado == estado)
    return q.order_by(DocumentoSunat.id.desc()).all()


def ventas_sin_documento(db: Session, sucursal_id: int | None = None) -> list[Venta]:
    """Ventas reales que todavía no tienen ningún documento SUNAT emitido
    encima — el hueco de control documental que este módulo existe para cerrar."""
    q = db.query(Venta)
    if sucursal_id is not None:
        q = q.filter(Venta.sucursal_id == sucursal_id)
    ventas = q.all()
    con_documento = {
        d.venta_id for d in db.query(DocumentoSunat).filter(DocumentoSunat.venta_id.isnot(None))
    }
    return [v for v in ventas if v.id not in con_documento]


def reporte_mermas_desmedros(db: Session, sucursal_id: int | None = None) -> dict:
    """Reporte para sustento SUNAT: separa MERMA (deducible sin trámite si
    está acreditada) de DESMEDRO (requiere destrucción/comunicación previa),
    con el valor valorizado de cada uno."""
    q = db.query(Merma)
    if sucursal_id is not None:
        from app.models.inventario import Almacen
        almacenes_ids = {a.id for a in db.query(Almacen).filter(Almacen.sucursal_id == sucursal_id)}
        q = q.filter(Merma.almacen_id.in_(almacenes_ids))
    registros = q.all()
    mermas = [m for m in registros if m.tipo_perdida == TipoPerdida.MERMA]
    desmedros = [m for m in registros if m.tipo_perdida == TipoPerdida.DESMEDRO]
    valor_mermas = sum((Decimal(str(m.costo_valorizado)) for m in mermas), Decimal("0"))
    valor_desmedros = sum((Decimal(str(m.costo_valorizado)) for m in desmedros), Decimal("0"))
    return {
        "mermas": {
            "cantidad_registros": len(mermas),
            "valor_total": float(valor_mermas),
            "detalle": [
                {"id": m.id, "producto_id": m.producto_id, "cantidad": float(m.cantidad),
                 "motivo": m.motivo, "valor": float(m.costo_valorizado),
                 "fecha": m.creado_en.isoformat() if m.creado_en else None}
                for m in mermas
            ],
        },
        "desmedros": {
            "cantidad_registros": len(desmedros),
            "valor_total": float(valor_desmedros),
            "detalle": [
                {"id": m.id, "producto_id": m.producto_id, "cantidad": float(m.cantidad),
                 "motivo": m.motivo, "valor": float(m.costo_valorizado),
                 "fecha": m.creado_en.isoformat() if m.creado_en else None}
                for m in desmedros
            ],
            "nota": "Para ser deducibles ante SUNAT requieren destrucción ante notario "
                    "o comunicación previa dentro de los 6 días hábiles siguientes, según el caso.",
        },
        "valor_total_perdidas": float(valor_mermas + valor_desmedros),
    }
