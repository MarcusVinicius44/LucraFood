# Desenvolvimento

Guia para quem vai rodar ou mexer no código. A apresentação do projeto está no [README](../README.md).

## Rodando localmente

Requisitos: Python 3.12+, Node 20+ e uma chave gratuita do Gemini ([AI Studio](https://aistudio.google.com)).

```bash
# backend (da raiz do repositório)
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # e cole sua GEMINI_API_KEY

cd backend
python manage.py migrate
python manage.py runserver       # http://localhost:8000
```

```bash
# frontend (em outro terminal)
cd frontend
npm install
npm run dev                      # http://localhost:5173 (o /api é repassado ao Django)
```

Para usar o Groq no lugar do Gemini: `LUCRAFOOD_PROVEDOR=groq` e `GROQ_API_KEY` no `.env`.

No Windows com o Controle Inteligente de Aplicativos ligado, o binário nativo do Rollup é bloqueado; por isso o `frontend/package.json` usa `overrides` para o `@rollup/wasm-node`.

## Testes

```bash
cd backend && python manage.py test cardapio     # IA mockada: não chama a API
cd frontend && npm test                          # vitest
cd frontend && npm run build                     # checa os tipos
```

## Avaliação com a API real

Gastam a cota do provedor (cada chamada conta, inclusive as que falham). Histórico em [AVALIACAO.md](AVALIACAO.md).

```bash
cd backend
python manage.py extrair_cardapio caminho/da/foto.jpg              # uma foto, mostra o JSON
python manage.py avaliar_extracao [--foto cardapio_01]             # fotos de evals/cardapios/
python manage.py avaliar_ficha [--frase f03]                       # frases de evals/fichas/
python manage.py avaliar_ficha --frases frases_revisao.json        # motivos de revisão
```

Regras: o prompt só muda com a avaliação rodada antes e depois, e os exemplos do prompt não podem vir das fotos ou frases de avaliação. Guarde a saída de cada rodada em `evals/*/resultados/`.

## API

| Método | Rota | O que faz |
|---|---|---|
| POST | `/api/cardapio/extrair/` | multipart com `imagem` → lista de pratos para conferência (não salva) |
| POST | `/api/cardapio/confirmar/` | JSON `{restaurante, pratos[]}` já conferido → salva |
| GET/PATCH | `/api/restaurantes/<id>/` | consulta/ajusta taxas, margem desejada (padrão 30) e margem mínima (padrão 10); mínima maior que desejada → 400 |
| GET/POST | `/api/restaurantes/<id>/ingredientes/` | lista/cadastra ingredientes como o dono compra (preço e tamanho da embalagem) |
| GET/PATCH/DELETE | `/api/ingredientes/<id>/` | edita/apaga; apagar ingrediente usado em ficha → 409 com os pratos |
| GET/PATCH | `/api/pratos/<id>/` | corrige preço de venda (ex.: o que veio nulo da foto), custo da embalagem e rendimento (porções que a receita rende; padrão 1, zero → 400) |
| GET/PUT | `/api/pratos/<id>/ficha/` | ficha com custo por item, custo da receita e diagnóstico; o PUT `{itens: [{ingrediente, quantidade}]}` troca a ficha inteira |
| GET | `/api/pratos/<id>/diagnostico/` | custo, margem balcão, margem delivery, semáforo e preço sugerido; sem preço ou sem ficha → sem semáforo |
| POST | `/api/pratos/<id>/ficha/extrair/` | JSON `{texto}` → itens lidos pela IA, com `precisa_confirmar` e motivos (não salva); texto sem ingredientes → 422 |
| POST | `/api/pratos/<id>/ficha/confirmar/` | ficha revisada pelo dono → salva (mesma validação do PUT, substitui a anterior) |

## Notas do dono

*ESCRITO POR MARCUS:*

- Precisamos pensar em que, quando o dono do restaurante fazer seu primeiro acesso e enviar a primeira foto do cardápio, ele não terá os produtos e ingredientes cadastrados, nem custos e quantidades de cada ingrediente. Então deve ser pensado num visual que traga o fluxo dos próximos passos bem intuitivo e facil de se entender e continuar, fazendo com que ele conclua todos os passos e ao final tenha o diagnóstico de lucro ou prejuízo de cada prato do cardápio.

(Atendida pelo painel "Próximos passos", que guia o dono da foto do cardápio até o diagnóstico de cada prato.)
