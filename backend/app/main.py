from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import (
    auth,
    calidad,
    competencia,
    compras,
    consultas,
    dashboard,
    inteligencia,
    lean,
    lean_captura,
    logistica,
    mermas,
    organizacion,
    produccion,
    productos,
    recetas,
    reportes,
    tributaria,
    ventas,
)

# Importar todos los modelos para que Base.metadata los conozca antes de create_all
from app.models import auth as _m_auth  # noqa: F401
from app.models import calidad as _m_calidad  # noqa: F401
from app.models import competencia as _m_competencia  # noqa: F401
from app.models import compras as _m_compras  # noqa: F401
from app.models import inventario as _m_inventario  # noqa: F401
from app.models import lean_captura as _m_lean_captura  # noqa: F401
from app.models import logistica as _m_logistica  # noqa: F401
from app.models import mermas as _m_mermas  # noqa: F401
from app.models import organizacion as _m_organizacion  # noqa: F401
from app.models import produccion as _m_produccion  # noqa: F401
from app.models import productos as _m_productos  # noqa: F401
from app.models import recetas as _m_recetas  # noqa: F401
from app.models import tributaria as _m_tributaria  # noqa: F401
from app.models import ventas as _m_ventas  # noqa: F401

app = FastAPI(title="Core ERP - Pastelería Industrial", version="0.1.0")

# CORS abierto: el frontend HTML (core_erp_dashboard.html) se abre como archivo local
# o se sirve desde otro origen, y necesita poder llamar a esta API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

    try:
        from seed import main as seed_main
        seed_main()
    except Exception as e:
        print(f"Seed omitido: {e}")

app.include_router(auth.router)
app.include_router(organizacion.router)
app.include_router(productos.router)
app.include_router(compras.router)
app.include_router(produccion.router)
app.include_router(ventas.router)
app.include_router(recetas.router)
app.include_router(mermas.router)
app.include_router(consultas.router)
app.include_router(dashboard.router)
app.include_router(lean.router)
app.include_router(inteligencia.router)
app.include_router(logistica.router)
app.include_router(reportes.router)
app.include_router(lean_captura.router)
app.include_router(calidad.router)
app.include_router(competencia.router)
app.include_router(tributaria.router)
