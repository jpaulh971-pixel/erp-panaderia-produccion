from datetime import datetime

from pydantic import BaseModel

from app.models.lean_captura import EstadoKaizen, TipoAndon


class Auditoria5SCrear(BaseModel):
    sucursal_id: int
    area: str
    seiri: int
    seiton: int
    seiso: int
    seiketsu: int
    shitsuke: int
    observaciones: str = ""
    auditor: str = ""


class KaizenCrear(BaseModel):
    sucursal_id: int
    area: str
    titulo: str
    descripcion: str = ""
    responsable: str = ""
    ahorro_estimado: float | None = None


class KaizenAvanzar(BaseModel):
    nuevo_estado: EstadoKaizen


class SmedCrear(BaseModel):
    sucursal_id: int
    proceso: str
    tiempo_setup_antes_min: float
    tiempo_setup_despues_min: float | None = None
    tiempo_interno_min: float | None = None
    tiempo_externo_min: float | None = None
    responsable: str = ""


class JidokaCrear(BaseModel):
    sucursal_id: int
    etapa: str
    motivo_paro: str
    op_id: int | None = None
    tiempo_paro_min: float | None = None


class JidokaResolver(BaseModel):
    accion_correctiva: str = ""


class AndonCrear(BaseModel):
    sucursal_id: int
    etapa: str
    tipo: TipoAndon
    descripcion: str = ""


class HeijunkaCrear(BaseModel):
    sucursal_id: int
    producto_id: int
    fecha: datetime
    cantidad_planificada: float


class HeijunkaActualizarReal(BaseModel):
    cantidad_real: float


class VsmPasoCrear(BaseModel):
    sucursal_id: int
    proceso: str
    orden: int
    nombre_paso: str
    tiempo_ciclo_min: float
    tiempo_espera_min: float = 0
    valor_agregado: bool = True
