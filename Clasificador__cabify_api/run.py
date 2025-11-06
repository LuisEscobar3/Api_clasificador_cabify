# run.py — lanza un servidor FastAPI con tu servicio de clasificación
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from requests import Session
from app.services import clasificar_poliza_por_placa

app = FastAPI(title="Clasificador de Pólizas", version="1.0.0")

# Permitir CORS (puedes restringir orígenes en producción)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

session = Session()

@app.get("/clasificar/{placa}")
def get_clasificacion(placa: str):
    try:
        result = clasificar_poliza_por_placa(session, placa)
        if result.get("clasificacion") in ["ERROR_EN_CONSULTA", "PLACA_INVALIDA"]:
            raise HTTPException(status_code=400, detail=result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})


@app.get("/")
def root():
    return {"mensaje": "API de clasificación de pólizas activa ✅"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("run:app", host="0.0.0.0", port=8000, reload=True)
