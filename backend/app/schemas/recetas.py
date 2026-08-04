from pydantic import BaseModel, ConfigDict


class RecetaIngredienteIn(BaseModel):
    insumo_id: int
    cantidad_por_unidad: float


class RecetaCrear(BaseModel):
    producto_id: int
    rendimiento_unidades: float
    ingredientes: list[RecetaIngredienteIn]
    merma_estimada_pct: float = 0.0


class RecetaIngredienteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    insumo_id: int
    cantidad_por_unidad: float


class RecetaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    producto_id: int
    version: int
    rendimiento_unidades: float
    merma_estimada_pct: float
    activa: bool
    ingredientes: list[RecetaIngredienteOut]
