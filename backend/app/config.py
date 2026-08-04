import os

SECRET_KEY = os.environ.get("CORE_ERP_SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8

LABOR_PCT_DEFAULT = 0.15
CIF_PCT_DEFAULT = 0.10
MARGEN_OBJETIVO_DEFAULT = 0.12

DATABASE_URL = os.environ.get("CORE_ERP_DATABASE_URL", "sqlite:///./core_erp.db")
