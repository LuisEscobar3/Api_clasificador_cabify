from typing import Optional
from pydantic import BaseModel

class ClasificacionResponse(BaseModel):
    clasificacion: str
    estado_poliza: Optional[str] = None
    fuente: str  # "bd" | "api"
    cobertura_368: bool
    error: Optional[str] = None
