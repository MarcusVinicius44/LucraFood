# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projeto

LucraFood: o dono de um restaurante pequeno fotografa o cardápio, a IA extrai os pratos, e o sistema calcula custo, margem (balcão x delivery) e um semáforo verde/amarelo/vermelho por prato. Produto e código em português (nomes de modelos, funções, rotas e mensagens de erro).

## Comandos

Rodar da raiz com o venv ativo (`python -m venv .venv`, `.venv\Scripts\activate` no Windows, `pip install -r requirements.txt`, `.env` copiado de `.env.example` com a chave do provedor, `GEMINI_API_KEY` (padrão) ou `GROQ_API_KEY` com `LUCRAFOOD_PROVEDOR=groq`). Os comandos Django rodam dentro de `backend/`.

```bash
cd backend
python manage.py migrate
python manage.py runserver
python manage.py test cardapio                                   # todos os testes (IA mockada, sem rede)
python manage.py test cardapio.tests.CalculosTest.test_custo_prato   # um teste
python manage.py extrair_cardapio caminho/da/foto.jpg            # chama a API real com uma foto
```

Não há linter configurado. O frontend (React + TypeScript, Vite em `localhost:5173`) ainda não existe; o CORS já está liberado para essa origem em `config/settings.py`.

## Arquitetura

Backend Django 5.2 + DRF, um único app `backend/cardapio/`, SQLite local.

- **`calculos.py`: toda a matemática** (custo do prato, margem, preço sugerido, `diagnosticar` que gera o semáforo). O semáforo usa a margem do delivery: verde ≥ `margem_desejada_pct` (padrão 30), vermelho < `margem_minima_pct` (padrão 10), amarelo no meio; limiar `None` cai no padrão, e mínima > desejada é `ValueError`. Python puro com `Decimal`, sem Django nem IA. Regra central do projeto: **o LLM nunca faz conta**, só extrai dados e conversa. Qualquer cálculo financeiro novo vai aqui, com teste em `tests.py`. Percentuais entram como 0–100 (23 = 23%).
- **`ia/`: camada de IA.** `cliente.py` usa a biblioteca `openai` apontada para um provedor com API compatível: `LUCRAFOOD_PROVEDOR=gemini|groq` no `.env` (padrão gemini, `PROVEDOR_PADRAO`; variável ausente ou vazia cai no padrão), com chave e modelo por provedor (`GROQ_API_KEY`/`GROQ_MODELO_VISAO`, `GEMINI_API_KEY`/`GEMINI_MODELO_VISAO`) e padrões de `max_tokens`/limitador em `PADROES`. Limites do plano gratuito: Groq ~1000 tokens de saída/min e recusa `max_tokens` acima disso (por isso teto 900 + limitador); Gemini (AI Studio, conferido em 06/11/2026) conta chamadas e tokens de entrada: 3.5 Flash-Lite 15 RPM / 250K TPM / 500 RPD, 3.8 Flash 5 RPM / 250K TPM / 20 RPD. Chamadas que voltam 503 também contam no RPD. `extracao.py` faz foto → `CardapioExtraido` (Pydantic): resposta JSON validada, com **uma** nova tentativa devolvendo o erro de validação ao modelo, e `ValueError` se falhar de novo (a view converte em 502). Também remove blocos `<think>` e cercas ``` antes de parsear. Preço ilegível vira `null`, nunca chute. Erros do provedor: 429 espera o retry-after (3 tentativas, depois `FalhaDeCota` → view 429); 503 espera 10 s e 30 s (3 tentativas, depois `ProvedorIndisponivel` → view 503). Foto que não dá para ler (o modelo devolve `foto_ilegivel` ou nenhum prato) vira `FotoIlegivel` → view **422** com `codigo: "foto_ilegivel"` pedindo outra foto. Pratos com vários preços vêm como `precos` + `colunas_preco` e são expandidos em "Nome (rótulo impresso)"; "tamanho N" só sem rótulo legível. `faixas.py`/`limitador.py` permitem ler a foto em faixas (útil no Groq; no Gemini basta a foto inteira).
- **Fluxo em duas etapas, nada grava sem confirmação humana:** `POST /api/cardapio/extrair/` (multipart `imagem`, JPG/PNG/WEBP até 4 MB, não salva) → dono confere/corrige → `POST /api/cardapio/confirmar/` (JSON `{restaurante, pratos[]}`) grava `Prato`s. `GET/PATCH /api/restaurantes/<id>/` consulta e ajusta taxas e limiares do semáforo; `margem_minima_pct > margem_desejada_pct` devolve 400 (validação duplicada no serializer e em `Restaurante.clean`, com a mesma mensagem `MSG_MINIMA_MAIOR`). As rotas ficam em `cardapio/urls.py`, sob `/api/`.
- **`models.py`:** `Restaurante` guarda taxa de delivery, impostos, margem desejada e margem mínima (percentuais por restaurante, nada fixo no código); `Ingrediente` guarda preço e tamanho da embalagem (custo unitário = preço / quantidade, propriedade `custo_por_unidade`); `Prato` → `ItemFichaTecnica` → `Ingrediente`. A ficha técnica ainda não tem endpoint nem agente (próximo item do roadmap, previsto com tool calling).
- **Testes** (`cardapio/tests.py`) usam um cliente de IA falso injetado em `extrair_cardapio(cliente=...)`; mantenha esse padrão para não chamar a API real.
- **`evals/cardapios/`:** fotos reais de cardápio + gabarito JSON de mesmo nome (formato da extração). `python manage.py avaliar_extracao [--foto cardapio_01]` roda a extração **real** (gasta a cota do provedor; cada chamada, inclusive as que falham, conta no limite diário) e mostra por foto e no total: encontrados, faltando, inventados, preços errados, tokens, chamadas e tempo. Referência em 08/11/2026 (Gemini 3.5 Flash-Lite, foto inteira): 251/254 pratos e 251/251 preços (outra rodada do mesmo dia: 246/254, o modelo varia na foto 05); histórico no README, "Evolução da extração". Exemplos dentro do prompt não podem vir das fotos de avaliação (senão a métrica mede algo "decorado"). A lógica de comparação é pura, em `cardapio/avaliacao.py` (testada sem API). Só nome e preço pontuam. O prompt de extração não deve ser alterado sem rodar a avaliação antes e depois.

## Docs de planejamento

`BRIEFING.md` (visão, escopo, regras de negócio, roadmap) e `AGENTES_E_SKILLS.md` (agentes/skills de desenvolvimento e agentes do produto) estão alinhados com a stack real. Em caso de conflito, vale o código e o `README.md`.
