"""Configuración común de pruebas: variables de entorno deterministas."""
import os
import sys
from pathlib import Path

os.environ.setdefault("JWT_SECRET", "secreto-de-pruebas-con-mas-de-32-caracteres-ok")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://soc_app:soc_app@localhost:5432/soclite_test")
os.environ.setdefault("ENVIRONMENT", "dev")
os.environ.setdefault("REPORTS_DIR", str(Path(__file__).parent / "_reports"))

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
