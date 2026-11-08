# LucraFood

> O dono do restaurante tira uma foto do cardápio e descobre quais pratos dão lucro e quais dão prejuízo no delivery.

Pequenos restaurantes costumam precificar no "achismo". Quando entram em aplicativos de delivery, taxas e impostos comem a margem sem que o dono perceba. O LucraFood usa IA para tirar o trabalho chato do caminho (digitar cardápio, montar ficha técnica) e entrega um diagnóstico simples: 🟢 🟡 🔴 por prato.

## Como funciona

1. **Foto do cardápio → pratos estruturados** (modelo de visão, saída JSON validada).
2. **Ficha técnica por texto** — o dono escreve o que vai no prato ("pão, hambúrguer de 150g, 2 fatias de queijo"), a IA liga cada item a um ingrediente cadastrado e o dono revisa antes de salvar. Medidas informais (fatia, concha) não viram gramas: o dono informa.
3. **Diagnóstico** — custo, margem no balcão, margem no delivery e preço sugerido.

## Decisões de engenharia

- **A IA não faz contas.** Ela extrai dados e conduz a conversa; toda a matemática está em [`calculos.py`](backend/cardapio/calculos.py), em Python puro com `Decimal`. LLMs erram aritmética, e preço errado custa dinheiro ao restaurante.
- **Saída estruturada e validada.** A resposta do modelo passa por Pydantic. Se falhar, o erro volta para o modelo e há uma nova tentativa; se falhar de novo, o usuário recebe um erro claro em vez de dados inventados.
- **Sem chute.** Preço ilegível vira `null`; ingrediente que não está no cadastro vira `null` (o id devolvido pela IA é conferido no Python); "2 fatias" não vira gramas. O dono confere antes de salvar: nada é gravado sem confirmação humana.
- **Provedor trocável.** Usa a biblioteca `openai` com a API compatível do provedor: Gemini por padrão, Groq como alternativa. Mudar de modelo ou provedor é uma variável de ambiente (`LUCRAFOOD_PROVEDOR`).
- **Avaliação medida, não "parece que funciona".** `evals/cardapios/` reúne fotos reais com gabarito, e `python manage.py avaliar_extracao` mede encontrados, faltando, inventados e preços errados. Resultado atual: 251 de 254 pratos e 251 de 251 preços em 8 fotos (ver [Evolução da extração](#evolução-da-extração)). A ficha por texto tem o seu conjunto em `evals/fichas/` e o comando `avaliar_ficha`.

## Evolução da extração

Medida com `python manage.py avaliar_extracao` (dentro de `backend/`) sobre as 8 fotos de `evals/cardapios/` (254 pratos no gabarito). Um prato conta como "encontrado" se o nome bate com o gabarito; o preço é conferido só entre os encontrados. Cada rodada chama a API de verdade e gasta a cota do provedor.

| Data | Provedor e modelo | Como lê a foto | Fotos completas | Pratos | Preços certos | Tempo |
|---|---|---|---|---|---|---|
| 08/11/2026 | Groq `qwen/qwen3.8-27b` | foto inteira | 3 de 8: as outras 5 cortaram no teto de 900 tokens de saída | 21 de 23 (nas 3 fotos) | 21 de 21 | 131 s |
| 08/11/2026 | Gemini `gemini-3.5-flash-lite` | foto inteira | **8 de 8** | **251 de 254 (98,8%)** | **251 de 251** | 39 s (~5 s por foto) |

Comandos (a rodada do Groq usou `LUCRAFOOD_PROVEDOR=groq` só no comando; desde `c1bb967` o padrão é o Gemini):

```bash
cd backend
LUCRAFOOD_PROVEDOR=groq python manage.py avaliar_extracao   # Groq, foto inteira
python manage.py avaliar_extracao                           # Gemini (padrão)
```

- **Por que o Groq não serve no plano gratuito:** ele limita ~1.000 tokens de saída por minuto e recusa pedidos com `max_tokens` acima disso. Por isso o teto é 900, e o JSON de um cardápio grande (até ~4.700 tokens no Gemini) não cabe. Também testei dividir a foto em 3 faixas ([`a0fe275`](https://github.com/MarcusVinicius44/LucraFood/commit/a0fe275)): só 3 de 8 fotos completaram, por isso troquei de provedor.
- **O Gemini varia entre rodadas.** Outra rodada do mesmo dia, com o mesmo prompt, deu **246 de 254** pratos (246 de 246 preços, 67 s): na foto 05, além dos caldinhos, os pastéis também vieram sem o tipo no nome ("Queijo" em vez de "Pastel de Queijo").
- **Limitações conhecidas** (não corrigidas no prompt): na foto 05 os caldinhos vêm só com o sabor ("Sururu" em vez de "Caldinho de Sururu") em todas as rodadas; na foto 02 o título de seção "HAMBURGUER DE PICANHA" às vezes é lido como prato (1 de 2 rodadas).
- **Sobre os gabaritos:** foram montados com ajuda de IA e conferidos ampliando a foto onde a extração discordava. Todos os "preços errados" encontrados até agora eram erro do gabarito ([`9e72ac4`](https://github.com/MarcusVinicius44/LucraFood/commit/9e72ac4)).

### Ficha técnica por texto

`python manage.py avaliar_ficha` sobre as 10 frases de `evals/fichas/` (42 ingredientes esperados, cadastro fictício de 21 itens), cada uma cobrindo um caso: sinônimo, pão sem número, kg e litro com vírgula, concha/xícara/fio, ingrediente fora do cadastro, queijo parecido mas diferente, erro de digitação e texto com ruído.

| Data | Provedor e modelo | Ingrediente certo | Quantidade certa | Ligados ao ingrediente errado | Chamadas |
|---|---|---|---|---|---|
| 08/11/2026 | Gemini `gemini-3.5-flash-lite` | 40 de 42 (95,2%) | 33 de 33 | 0 | 10 (~1 s por frase) |

- Duas rodadas no mesmo dia deram o mesmo resultado. Os 2 erros são "queijo" (frases f07 e f09) que ficou sem ingrediente em vez de "Queijo prato": é a falha segura, porque o dono escolhe na revisão em vez de receber um custo errado.
- **As respostas esperadas são um rascunho escrito por IA e ainda não revisado.** Os números acima valem para esse rascunho.

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
| GET/POST | `/api/restaurantes/<id>/ingredientes/` | lista/cadastra ingredientes como o dono compra (preço e tamanho da embalagem) |
| GET/PATCH/DELETE | `/api/ingredientes/<id>/` | edita/apaga; apagar ingrediente usado em ficha → 409 com os pratos |
| GET/PATCH | `/api/pratos/<id>/` | corrige preço de venda (ex.: o que veio nulo da foto) e custo da embalagem |
| GET/PUT | `/api/pratos/<id>/ficha/` | ficha com custo por item e diagnóstico; o PUT `{itens: [{ingrediente, quantidade}]}` troca a ficha inteira |
| GET | `/api/pratos/<id>/diagnostico/` | custo, margem balcão, margem delivery, semáforo e preço sugerido; sem preço ou sem ficha → sem semáforo |
| POST | `/api/pratos/<id>/ficha/extrair/` | JSON `{texto}` → itens lidos pela IA, com `precisa_confirmar` e motivos (não salva); texto sem ingredientes → 422 |
| POST | `/api/pratos/<id>/ficha/confirmar/` | ficha revisada pelo dono → salva (mesma validação do PUT, substitui a anterior) |

## Roadmap

- [x] Extração de cardápio por foto com validação e retry
- [x] Motor de cálculo de custo, margem e preço sugerido (com testes)
- [x] Ficha técnica: ingredientes, ficha por prato, diagnóstico e extração por texto com revisão
- [ ] **Próximo passo:** ficha em conversa de várias rodadas (a IA pergunta o que faltou: "quantos gramas tem a fatia de queijo?")
- [ ] Painel com semáforo e simulador de preço (React)
- [x] Conjunto de avaliação com fotos reais e métricas
- [ ] Teste com restaurantes de verdade
