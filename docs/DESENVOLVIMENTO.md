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
npm run dev                      # http://localhost:5173 = landing; o app fica em /app (o /api é repassado ao Django)
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
python manage.py avaliar_conversa [--resposta c03]                 # respostas da ficha em conversa
```

Regras: o prompt só muda com a avaliação rodada antes e depois, e os exemplos do prompt não podem vir das fotos ou frases de avaliação. Guarde a saída de cada rodada em `evals/*/resultados/`.

## Landing, demo e publicação

O frontend tem duas partes: a landing com a demo em `/` (`src/landing/`, `src/demo/`) e o app em `/app` (`src/telas/`). A demo nunca chama `/api`: ela usa respostas gravadas da IA e as contas de `src/demo/calculosDemo.ts`.

```bash
cd backend
python manage.py gravar_demo [--so-fichas]   # CHAMA A API: regrava as respostas da demo (1 chamada da foto + 1 por frase)
python manage.py gerar_casos_demo            # sem IA: regenera os casos que comparam calculosDemo.ts com calculos.py
```

- Entradas da demo (fictícias): `frontend/src/demo/fixtures/cardapio-sabor-da-esquina.html` (gera o PNG; o comando está no comentário do arquivo) e `entrada-demo.json` (cadastro, taxas e frases). Saídas: `gravado-extracao.json` e `gravado-fichas.json`.
- Mudou `calculos.py`? Mude `calculosDemo.ts` igual, rode `gerar_casos_demo` e `npm test`.
- Imagem de prévia (LinkedIn/WhatsApp): `marca/og-lucrafood.html` → `frontend/public/og-lucrafood.png` (comando no comentário do HTML).

**Publicar na Vercel (só o frontend):**

1. Na Vercel, *Add New → Project* e importe o repositório.
2. Em *Root Directory*, escolha `frontend`. O resto vem do `frontend/vercel.json`: build com `VITE_SEM_BACKEND=1` (o `/app` mostra o aviso "O app completo roda com o back-end") e o fallback de rotas do SPA (abrir `/app/painel` direto funciona).
3. *Deploy*. As meta tags de prévia usam o domínio de produção da Vercel; com domínio próprio, defina `VITE_SITE_URL=https://seu-dominio` nas variáveis de ambiente do projeto.

Para ver a versão publicada localmente: `cd frontend && VITE_SEM_BACKEND=1 npm run build && npx vite preview`.

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
| POST | `/api/pratos/<id>/ficha/conversa/` | ficha em conversa: `{itens, pulados, pergunta?, resposta?}` → item atualizado e próxima pergunta (sem resposta, só a primeira pergunta e sem IA; não salva) |
| POST | `/api/pratos/<id>/ficha/confirmar/` | ficha revisada pelo dono → salva (mesma validação do PUT, substitui a anterior); `medidas` opcional (`[{ingrediente, medida, quantidade}]`, o que o dono ensinou na conversa) é gravado junto |
| DELETE | `/api/medidas/<id>/` | esquece uma medida ensinada ("1 fatia = 18 g"); as medidas aparecem em `medidas` de cada ingrediente |

## Notas do dono

*ESCRITO POR MARCUS:*

- Precisamos pensar em que, quando o dono do restaurante fazer seu primeiro acesso e enviar a primeira foto do cardápio, ele não terá os produtos e ingredientes cadastrados, nem custos e quantidades de cada ingrediente. Então deve ser pensado num visual que traga o fluxo dos próximos passos bem intuitivo e facil de se entender e continuar, fazendo com que ele conclua todos os passos e ao final tenha o diagnóstico de lucro ou prejuízo de cada prato do cardápio.

(Atendida pelo painel "Próximos passos", que guia o dono da foto do cardápio até o diagnóstico de cada prato.)
