# LucraFood

> O dono do restaurante tira uma foto do cardápio e descobre quais pratos dão lucro e quais dão prejuízo no delivery.

Pequenos restaurantes costumam precificar no "achismo". Quando entram em aplicativos de delivery, taxas e impostos comem a margem sem que o dono perceba. O LucraFood usa IA para tirar o trabalho chato do caminho (digitar cardápio, montar ficha técnica) e entrega um diagnóstico simples: 🟢 🟡 🔴 por prato.

## Como funciona

1. **Foto do cardápio → pratos estruturados** (modelo de visão, saída JSON validada).
2. **Ficha técnica conversada** — um agente pergunta quanto de cada ingrediente vai em cada prato. *(em construção)*
3. **Diagnóstico** — custo, margem no balcão, margem no delivery e preço sugerido.

## Decisões de engenharia

- **A IA não faz contas.** Ela extrai dados e conduz a conversa; toda a matemática está em [`calculos.py`](backend/cardapio/calculos.py), em Python puro com `Decimal`. LLMs erram aritmética, e preço errado custa dinheiro ao restaurante.
- **Saída estruturada e validada.** A resposta do modelo passa por Pydantic. Se falhar, o erro volta para o modelo e há uma nova tentativa; se falhar de novo, o usuário recebe um erro claro em vez de dados inventados.
- **Sem chute de preço.** Preço ilegível vira `null` e o dono confere antes de salvar. Nada é gravado sem confirmação humana.
- **Provedor trocável.** Usa a biblioteca `openai` com a API compatível do provedor: Gemini por padrão, Groq como alternativa. Mudar de modelo ou provedor é uma variável de ambiente (`LUCRAFOOD_PROVEDOR`).
- **Avaliação medida, não "parece que funciona".** `evals/cardapios/` reúne fotos reais com gabarito, e `python manage.py avaliar_extracao` mede encontrados, faltando, inventados e preços errados. *(1 foto avaliada por enquanto)*

## Stack

Django + DRF · React + TypeScript *(em construção)* · Gemini 3.5 Flash-Lite (visão + JSON; Groq `qwen/qwen3.8-27b` como alternativa) · Pydantic

## Rodando localmente

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # e cole sua GEMINI_API_KEY (aistudio.google.com)

cd backend
python manage.py migrate
python manage.py test cardapio   # testes não usam a API (IA mockada)

# teste rápido com uma foto real:
python manage.py extrair_cardapio caminho/da/foto.jpg

python manage.py runserver
```

### API

| Método | Rota | O que faz |
|---|---|---|
| POST | `/api/cardapio/extrair/` | multipart com `imagem` → lista de pratos para conferência (não salva) |
| POST | `/api/cardapio/confirmar/` | JSON `{restaurante, pratos[]}` já conferido → salva |
| GET/PATCH | `/api/restaurantes/<id>/` | consulta/ajusta taxas, margem desejada (padrão 30) e margem mínima (padrão 10); mínima maior que desejada → 400 |

## Roadmap

- [x] Extração de cardápio por foto com validação e retry
- [x] Motor de cálculo de custo, margem e preço sugerido (com testes)
- [ ] Agente de ficha técnica com tool calling
- [ ] Painel com semáforo e simulador de preço (React)
- [ ] Conjunto de avaliação com fotos reais e métricas
- [ ] Teste com restaurantes de verdade
