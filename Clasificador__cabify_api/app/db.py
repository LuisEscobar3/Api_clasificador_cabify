import psycopg2
from psycopg2.extras import RealDictCursor
from Clasificador__cabify_api.app.settings import settings

def ejecutar_consulta(query: str, params: tuple = None):
    conn = None
    try:
        conn = psycopg2.connect(
            host=settings.PG_HOST,
            port=settings.PG_PORT,
            dbname=settings.PG_DB,
            user=settings.PG_USER,
            password=settings.PG_PASS,
        )
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            if query.strip().lower().startswith("select"):
                return cur.fetchall() or []
            conn.commit()
            return {"status": "ok", "rows_affected": cur.rowcount}
    finally:
        if conn:
            conn.close()

def buscar_por_placa(placa: str):
    """
    Devuelve dict con los campos (si existe) o None si no hay filas.
    """
    q = """
        SELECT id, numero_poliza, codigo_riesgo, codigo_opcion_tarifa, placa_mas_reciente
        FROM public.placas_vhr
        WHERE placa_mas_reciente = %s
        LIMIT 1;
    """
    rows = ejecutar_consulta(q, (placa,))
    if not rows:
        return None
    # rows[0] es RealDictRow -> convertir a dict nativo
    return dict(rows[0])
