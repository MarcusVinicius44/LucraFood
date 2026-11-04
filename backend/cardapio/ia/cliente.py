"""Cliente de IA.

Usa a biblioteca `openai` apontando para o Groq (API compatível com OpenAI).
Trocar de provedor = trocar GROQ_BASE_URL e o nome do modelo no .env.
"""
import os
from functools import lru_cache

from openai import OpenAI

BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
MODELO_VISAO = os.getenv("LUCRAFOOD_MODELO_VISAO", "qwen/qwen3.8-27b")


@lru_cache
def get_cliente() -> OpenAI:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("Defina GROQ_API_KEY no arquivo .env (veja .env.example).")
    return OpenAI(api_key=api_key, base_url=BASE_URL)
