import os

# Carga .env si lo usas (opcional)
from dotenv import load_dotenv
load_dotenv()

class Settings:
    # Postgres
    PG_HOST = os.getenv("PG_HOST", "18.224.149.147")
    PG_PORT = int(os.getenv("PG_PORT", "5432"))
    PG_DB   = os.getenv("PG_DB", "vig_autos")
    PG_USER = os.getenv("PG_USER", "remoto")
    PG_PASS = os.getenv("PG_PASS", "Segur14j@i")

    # REST Portafolio
    API_URL = os.getenv("API_URL", "https://api-portafolio-full-b8e7pwut.uc.gateway.dev/portafolio")
    API_KEY = os.getenv("API_KEY", "AIzaSyBJ8bgApSZtMcYG88RV8hPAWs1mboJ4K78")
    DOCUMENTO = os.getenv("DOCUMENTO", "00000000")

    # OAuth / GraphQL
    OAUTH_URL = os.getenv("OAUTH_URL", "https://api-conecta.segurosbolivar.com/prod/oauth2/token")
    CLIENT_ID = os.getenv("CLIENT_ID", "4oha8gka92tbv1205g89j6l8f4")
    CLIENT_SECRET = os.getenv("CLIENT_SECRET", "io0lkclq2rtespm3on2t59gt75165ibq74lpi0oaebdvvvn3l9l")
    SCOPE = os.getenv("SCOPE", "SrcServerCognitoConecta/ConectaApiScope")
    GRAPHQL_URL = os.getenv("GRAPHQL_URL", "https://api-conecta.segurosbolivar.com/prod/dataops/graphql/cliente")
    USER_KEY = os.getenv("USER_KEY", "bc26092b2cfe4a54b123d1824e442057")

    # Salario mínimo (para reglas)
    SALARIO_MINIMO_VIGENTE = int(os.getenv("SALARIO_MINIMO_VIGENTE", "1423500"))

settings = Settings()
