"""Cliente de IA.

Usa a biblioteca `openai` apontando para um provedor com API compatível (Groq ou Gemini).
Trocar de provedor = `LUCRAFOOD_PROVEDOR` no .env. Cada provedor tem seus padrões de URL,
chave, modelo, teto de saída por chamada e limites por minuto; qualquer um pode ser
sobrescrito por variável de ambiente (veja .env.example).
"""
import os
from dataclasses import dataclass
from functools import lru_cache

from openai import OpenAI

PADROES = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "modelo": "qwen/qwen3.8-27b",
        # O plano gratuito limita ~1000 tokens de SAÍDA/min e recusa (429) pedidos cujo
        # max_tokens passe disso; e ~8000 tokens no total/min.
        "max_tokens": 900,
        "limite_saida_min": 1000,
        "limite_tokens_min": 8000,
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "modelo": "gemini-3.5-flash-lite",
        # O limite por minuto do Gemini é de tokens de ENTRADA (e de chamadas), não de saída.
        "max_tokens": 8192,
        "limite_saida_min": 0,  # 0 = sem limitador de saída
        "limite_tokens_min": 0,  # 0 = sem aviso
    },
}


@dataclass(frozen=True)
class Config:
    provedor: str
    base_url: str
    var_chave: str
    modelo: str
    max_tokens: int
    limite_saida_min: int
    limite_tokens_min: int


def _int(var: str, padrao: int) -> int:
    valor = os.getenv(var)
    return int(valor) if valor not in (None, "") else padrao


def config() -> Config:
    """Lê o provedor e os ajustes do ambiente (.env), com os padrões do provedor.

    Variáveis por provedor (PREFIXO = GROQ ou GEMINI): {PREFIXO}_API_KEY, {PREFIXO}_BASE_URL,
    {PREFIXO}_MODELO_VISAO. LUCRAFOOD_MODELO_VISAO ainda vale para o Groq (nome antigo).
    """
    provedor = os.getenv("LUCRAFOOD_PROVEDOR", "groq").strip().lower()
    if provedor not in PADROES:
        raise RuntimeError(f"LUCRAFOOD_PROVEDOR inválido: {provedor!r}. Use um de: {', '.join(PADROES)}.")
    p = PADROES[provedor]
    prefixo = provedor.upper()
    modelo = os.getenv(f"{prefixo}_MODELO_VISAO")
    if not modelo and provedor == "groq":
        modelo = os.getenv("LUCRAFOOD_MODELO_VISAO")
    return Config(
        provedor=provedor,
        base_url=os.getenv(f"{prefixo}_BASE_URL") or p["base_url"],
        var_chave=f"{prefixo}_API_KEY",
        modelo=modelo or p["modelo"],
        max_tokens=_int("LUCRAFOOD_MAX_TOKENS", p["max_tokens"]),
        limite_saida_min=_int("LUCRAFOOD_LIMITE_SAIDA_MIN", p["limite_saida_min"]),
        limite_tokens_min=_int("LUCRAFOOD_LIMITE_TOKENS_MIN", p["limite_tokens_min"]),
    )


@lru_cache
def get_cliente() -> OpenAI:
    cfg = config()
    api_key = os.getenv(cfg.var_chave)
    if not api_key:
        raise RuntimeError(f"Defina {cfg.var_chave} no arquivo .env (veja .env.example).")
    # max_retries=0: o retry de 429 é nosso (extracao._chamar), para respeitar retry-after e contar tentativas.
    return OpenAI(api_key=api_key, base_url=cfg.base_url, max_retries=0)
