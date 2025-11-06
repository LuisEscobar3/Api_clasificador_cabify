# services.py
# -*- coding: utf-8 -*-
"""
Servicios de clasificación por placa:
- Consulta en BD (prioritario) y, si no hay, consulta API REST (x-api-key).
- (Opcional) Consulta GraphQL para estadoPoliza si el REST devuelve documento.
- Clasificación SOLO: PREMIUM / ESTANDAR / NO_CLASIFICADO.
- Respuesta consistente (dict):
  {
    "clasificacion": str,
    "estado_poliza": Optional[str],
    "fuente": "bd" | "api" | "none",
    "cobertura_368": bool,
    "error": Optional[str]
  }
"""

import base64
import json
from typing import Any, Dict, List, Optional, Tuple

import requests
from app.settings import settings
from app.db import buscar_por_placa

# ========== Reglas usadas (solo PREMIUM / ESTANDAR) ==========
REGLAS_PREMIUM = {
    "VALOR_RC": 4_000_000_000,
    "OPCIONES_DEDUCIBLE": [800_000, int(settings.SALARIO_MINIMO_VIGENTE * 0.8)],
}
REGLAS_ESTANDAR = {
    "VALOR_RC": 2_200_000_000,
    "OPCIONES_DEDUCIBLE": [975_000, settings.SALARIO_MINIMO_VIGENTE],
}


# ========== Helpers ==========
def _as_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        s = value.strip()
        for ch in ("$", ".", ",", " "):
            s = s.replace(ch, "")
        if s in ("", "-"):
            return None
        try:
            return int(s)
        except ValueError:
            return None
    return None


def _find_coverage(items: List[Dict[str, Any]], codigo_cobertura: int) -> Optional[Dict[str, Any]]:
    for it in items:
        code = _as_int(it.get("CODIGO_COBERTURA"))
        if code == codigo_cobertura:
            return it
    return None


def _extraer_doc_de_portafolio(coberturas: List[Dict[str, Any]]) -> Tuple[Optional[str], Optional[str]]:
    for c in coberturas:
        num = c.get("NUMERO_DOCUMENTO_ASEGURADO")
        tipo = c.get("TIPO_DOCUMENTO_ASEGURADO") or "CC"
        if num:
            return str(num), str(tipo)
    return None, None


# ========== OAuth / GraphQL ==========
def _generar_token(timeout: int = 30) -> Optional[str]:
    """OAuth2 client_credentials."""
    try:
        basic = f"{settings.CLIENT_ID}:{settings.CLIENT_SECRET}".encode("utf-8")
        basic_auth = base64.b64encode(basic).decode("utf-8")
        headers = {
            "Authorization": f"Basic {basic_auth}",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }
        data = {"grant_type": "client_credentials", "scope": settings.SCOPE}
        resp = requests.post(settings.OAUTH_URL, headers=headers, data=data, timeout=timeout)
        payload = resp.json()
        return payload.get("access_token")
    except Exception:
        return None


def _consultar_estado_poliza(
    session: requests.Session, tipo_documento: str, numero_documento: str, timeout: int = 40
) -> Optional[str]:
    token = _generar_token()
    if not token:
        return None

    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"Bearer {token}",
        "x-user-key": settings.USER_KEY,
    }
    query = """
    query Clientes($tipoDocumento: String!, $numeroDocumento: String!) {
      cliente(cliente: { tipoDocumento: $tipoDocumento, numeroDocumento: $numeroDocumento }) {
        portafolioVigente { estadoPoliza }
      }
    }
    """
    variables = {"tipoDocumento": tipo_documento or "CC", "numeroDocumento": str(numero_documento)}

    try:
        resp = session.post(
            settings.GRAPHQL_URL,
            headers=headers,
            json={"query": query, "variables": variables},
            timeout=timeout,
        )
        data = resp.json()
    except Exception:
        return None

    cliente = (data.get("data") or {}).get("cliente") or {}
    pv = cliente.get("portafolioVigente")
    if pv is None:
        return None
    if isinstance(pv, dict):
        return pv.get("estadoPoliza")
    if isinstance(pv, list):
        estados = [
            str(item.get("estadoPoliza"))
            for item in pv
            if isinstance(item, dict) and item.get("estadoPoliza")
        ]
        if not estados:
            return None
        for est in estados:
            if est.upper() == "VIGENTE":
                return est
        return estados[0]
    return None


# ========== REST Portafolio ==========
def consultar_portafolio(session: requests.Session, placa: str, timeout: int = 30):
    headers = {"x-api-key": settings.API_KEY, "Content-Type": "application/json"}
    body = {"documento": settings.DOCUMENTO, "placa": placa}
    try:
        resp = session.post(settings.API_URL, headers=headers, json=body, timeout=timeout)
        if resp.status_code != 200:
            return None, f"HTTP {resp.status_code}: {resp.text}"
        return resp.json(), None
    except requests.RequestException as e:
        return None, f"Network exception: {e}"


# ========== Clasificación (solo PREMIUM / ESTANDAR) ==========
def _determinar_tipo_por_valores(valor_rc: Optional[int], valor_deducible: Optional[int]) -> str:
    """
    Determina únicamente 'PREMIUM', 'ESTANDAR' o 'NO_CLASIFICADO'
    usando la regla de 'cualquiera de las dos' (RC o DED).
    """
    if valor_rc is None and valor_deducible is None:
        return "NO_CLASIFICADO"

    es_premium_rc = (valor_rc is not None) and (valor_rc >= REGLAS_PREMIUM["VALOR_RC"])
    es_premium_ded = (valor_deducible is not None) and (valor_deducible in REGLAS_PREMIUM["OPCIONES_DEDUCIBLE"])
    if es_premium_rc or es_premium_ded:
        return "PREMIUM"

    es_estandar_rc = (valor_rc is not None) and (valor_rc >= REGLAS_ESTANDAR["VALOR_RC"])
    es_estandar_ded = (valor_deducible is not None) and (valor_deducible in REGLAS_ESTANDAR["OPCIONES_DEDUCIBLE"])
    if es_estandar_rc or es_estandar_ded:
        return "ESTANDAR"

    return "NO_CLASIFICADO"


def clasificar_poliza_por_placa(session: requests.Session, placa: str) -> Dict[str, Any]:
    """
    Flujo:
      1) Busca en BD (placas_vhr): si hay, clasifica por codigo_opcion_tarifa (1=PREMIUM, 2=ESTANDAR).
      2) Si no hay en BD, consulta REST (portafolio) -> lee coberturas 370 (RC), 372 (DED), 368 (VHR).
      3) Devuelve dict consistente.
    """
    if not placa or not isinstance(placa, str) or not placa.strip():
        return {
            "clasificacion": "PLACA_INVALIDA",
            "estado_poliza": None,
            "fuente": "none",
            "cobertura_368": False,
            "error": None,
        }

    placa = placa.strip().upper()

    # 1) Intentar BD primero
    fila = buscar_por_placa(placa)
    if fila:
        # buscar_por_placa debe devolver dict (no lista). Si devolviera lista, haz: fila = dict(fila[0]).
        colectiva_prefix = "COLECTIVA " if int(fila.get("codigo_riesgo", 0)) > 1 else ""
        cod_tarifa = str(fila.get("codigo_opcion_tarifa", "")).strip()
        if cod_tarifa == "1":
            tipo = "PREMIUM"
        elif cod_tarifa == "2":
            tipo = "ESTANDAR"
        else:
            tipo = "NO_CLASIFICADO"

        return {
            "clasificacion": f"{colectiva_prefix}{tipo}".strip(),
            "estado_poliza": None,   # si quieres, puedes llamar GraphQL aquí
            "fuente": "bd",
            "cobertura_368": False,  # desde BD no sabemos si existe la 368
            "error": None,
        }

    # 2) Si no está en BD, consultar REST
    resultado, err = consultar_portafolio(session, placa)
    if err or not resultado:
        return {
            "clasificacion": "ERROR_EN_CONSULTA",
            "estado_poliza": None,
            "fuente": "api",
            "cobertura_368": False,
            "error": err or "Sin datos",
        }

    # Normaliza a lista de coberturas
    if isinstance(resultado, dict):
        coberturas: List[Dict[str, Any]] = list(resultado.values())
    elif isinstance(resultado, list):
        coberturas = resultado
    else:
        return {
            "clasificacion": "ERROR_EN_CONSULTA",
            "estado_poliza": None,
            "fuente": "api",
            "cobertura_368": False,
            "error": "Formato desconocido",
        }

    # Documento para GraphQL
    numero_doc, tipo_doc = _extraer_doc_de_portafolio(coberturas)
    estado_poliza = _consultar_estado_poliza(session, tipo_doc or "CC", numero_doc) if numero_doc else None

    # Coberturas relevantes (IDs fijos)
    cobertura_rc = _find_coverage(coberturas, 370)   # RC
    cobertura_ded = _find_coverage(coberturas, 372)  # DED
    cobertura_vhr = _find_coverage(coberturas, 368)  # VHR
    cobertura_368_ok = cobertura_vhr is not None

    # Valores
    valor_rc = _as_int(cobertura_rc.get("VALOR_ASEGURADO")) if cobertura_rc else None
    valor_deducible = _as_int(cobertura_ded.get("VALOR_DEDUCIBLE")) if cobertura_ded else None
    codigo_riesgo = _as_int(cobertura_rc.get("CODIGO_RIESGO")) if cobertura_rc else None

    # Clasificar solo PREMIUM/ESTANDAR
    tipo = _determinar_tipo_por_valores(valor_rc, valor_deducible)
    colectiva_prefix = "COLECTIVA " if (codigo_riesgo and codigo_riesgo > 1) else ""
    clasificacion = f"{colectiva_prefix}{tipo}".strip()

    return {
        "clasificacion": clasificacion,
        "estado_poliza": estado_poliza,
        "fuente": "api",
        "cobertura_368": bool(cobertura_368_ok),
        "error": None,
    }
