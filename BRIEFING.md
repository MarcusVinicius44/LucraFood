# LucraFood — Briefing do Projeto

## 1. Visão geral
**LucraFood** é uma plataforma com um agente de IA embutido que ajuda donos de pequenas lanchonetes, marmitarias e restaurantes a descobrir **quanto cada prato realmente lucra** (no balcão e no delivery) e quais dão prejuízo.

**Pitch:** *"Tire uma foto do cardápio e descubra em minutos quais pratos dão lucro e quais dão prejuízo no delivery."*

## 2. Público-alvo
- **Usuário principal:** dono de lanchonete, marmitaria ou restaurante pequeno.
- Perfil: não tem nutricionista nem contador, cuida dos custos sozinho, muitas vezes sem planilha; usa principalmente o celular.
- Implicação de produto: interface **mobile-first**, linguagem simples (sem jargão contábil), mínimo de digitação.

## 3. Problema (a dor)
- Precifica no "achismo" ou copiando o concorrente.
- Não sabe o custo real de cada prato.
- Não enxerga o efeito das taxas de delivery (iFood etc.) na margem.
- Não sabe quais pratos puxam o lucro e quais o corroem.

## 4. Proposta de valor
Transformar um cardápio em fotografia + poucas respostas simples em um **diagnóstico de lucratividade por prato**, com semáforo (verde/amarelo/vermelho), sem planilha e sem conhecimento financeiro.

## 5. Fluxo do usuário
1. **Foto do cardápio** → a IA (visão) lê e gera a lista de pratos com nome, descrição e preço atual.
2. **Conferência** → o dono revisa e corrige o que a IA leu.
3. **Ingredientes e preços de compra** → o dono cadastra o que paga em cada insumo. *Extra:* enviar foto de nota de compra/nota fiscal e a IA extrai itens e preços.
4. **Ficha técnica conversada** → para cada prato a IA pergunta de forma simples. Ex.: *"No X-Tudo, quantas gramas de carne vão? E de queijo?"* A IA **sugere quantidades típicas** e o dono só confirma ou ajusta.
5. **Diagnóstico** → painel com custo, margem no balcão, margem no delivery e **semáforo por prato**.

## 6. Escopo do MVP
**Dentro:**
- Upload/foto de cardápio → extração de pratos (OCR + LLM), com tela de revisão.
- Cadastro de ingredientes com preço e unidade (kg, g, L, un).
- Ficha técnica por prato, montada por chat guiado, com sugestão de quantidades.
- Configuração de taxas do delivery (hoje: taxa do app % e impostos % por restaurante, embalagem por prato; margem desejada e mínima).
- Painel de diagnóstico: custo, lucro e margem (balcão x delivery) + semáforo.
- Ranking: pratos mais lucrativos / pratos com prejuízo.

**Fora do MVP (backlog):**
- Leitura de nota de compra por foto (começar como "extra" pós-MVP ou fase 2).
- Integração direta com iFood/POS, estoque, CMV por período, multiusuário/multiunidade.
- Sugestão automática de novo preço ("para ter 30% de margem, cobre R$ X").
- Simulador "e se" (subiu o preço da carne, o que acontece?).

## 7. Lógica de cálculo (regras de negócio)
*Implementado em `backend/cardapio/calculos.py`. Hoje há um único `preco_venda` por prato, usado no balcão e no delivery.*
- **Custo do prato** = Σ (quantidade do ingrediente × custo por unidade) + custo de embalagem do prato. O custo por unidade vem de preço da embalagem ÷ quantidade da embalagem.
- **Margem balcão** = (preço − custo − impostos%·preço) / preço.
- **Margem delivery** = (preço − custo − (taxa do app% + impostos%)·preço) / preço. A taxa do app é um único percentual por restaurante (comissão + pagamento somados).
- **Evolução prevista:** preço de delivery diferente do de balcão, comissão e taxa de pagamento separadas, embalagem só no delivery.
- **Semáforo** (sempre pela **margem do delivery**; limiares configuráveis por restaurante):
  - 🟢 verde: margem ≥ **margem desejada** (padrão 30% quando o restaurante não informa)
  - 🟡 amarelo: entre a margem mínima e a desejada
  - 🔴 vermelho: margem < **margem mínima** (padrão 10%); inclui prejuízo, mas não se limita a ele
  - Os limites são inclusivos para cima: margem igual à mínima é amarelo; igual à desejada é verde. A mínima não pode ser maior que a desejada.
  - Para pratos amarelos e vermelhos o sistema também calcula o preço sugerido de delivery que atinge a margem desejada.
- Tratar conversão de unidades (g↔kg, ml↔L) e rendimento/perda de insumos (ex.: fator de correção) como evolução.

## 8. Papel da IA
| Função | Tecnologia | Observações |
|---|---|---|
| Ler cardápio por foto | Modelo multimodal (visão) | Saída estruturada em JSON; sempre com tela de confirmação humana |
| Ler nota de compra | Modelo multimodal | Mapear itens da nota para ingredientes cadastrados |
| Ficha técnica conversada | LLM com tool use | Pergunta curta, sugere quantidades típicas, grava no banco via ferramentas |
| Explicar o diagnóstico | LLM | "Por que o X-Bacon está vermelho?" em linguagem simples |

Princípios: a IA **sugere, o dono confirma**; nunca gravar valores financeiros sem confirmação; deixar claro quando um número é estimativa da IA.

## 9. Stack (definida e em uso)
- **Back-end:** Django 5.2 + Django REST Framework, SQLite no desenvolvimento (app `backend/cardapio/`).
- **Front-end:** React + TypeScript (Vite, `localhost:5173`), mobile-first, captura de foto pela câmera. *Ainda não iniciado.*
- **IA:** Groq via biblioteca `openai` (API compatível), modelo `qwen/qwen3.8-27b` com visão, JSON e tool calling. Trocar de provedor ou modelo é só mudar variáveis no `.env`.
- **Validação:** Pydantic na saída da IA; cálculos em Python puro com `Decimal` (`calculos.py`).
- **Hospedagem:** a definir.

## 10. Modelo de dados
**Já implementado (`backend/cardapio/models.py`):**
- `Restaurante` (nome, `taxa_delivery_pct`, `impostos_pct`, `margem_desejada_pct` padrão 30, `margem_minima_pct` padrão 10)
- `Prato` (restaurante, nome, descricao, categoria, `preco_venda` opcional, `custo_embalagem`)
- `Ingrediente` (restaurante, nome, unidade g/ml/un, `preco_embalagem`, `quantidade_embalagem`)
- `ItemFichaTecnica` (prato, ingrediente, quantidade)
- O diagnóstico não é tabela: é calculado por `calculos.diagnosticar`.

**Previsto (ainda não existe):**
- `ItemFichaTecnica.origem` (ia_sugerida | confirmada_pelo_dono)
- Taxas por plataforma de delivery (comissão e pagamento separadas)
- `NotaCompra` (imagem, itens extraídos, status)

## 11. Métricas de sucesso
- Tempo do cadastro até o primeiro diagnóstico (meta: **< 15 min**).
- % de pratos com ficha técnica completa por usuário.
- Taxa de correção manual dos itens lidos da foto (qualidade da IA).
- Retenção semanal e nº de preços de pratos alterados após o diagnóstico (impacto real).

## 12. Riscos e pontos de atenção
- **Qualidade da leitura do cardápio** (fotos ruins, letra manuscrita, cardápios com combos/adicionais) → exigir revisão e permitir edição fácil.
- **Quantidades sugeridas pela IA podem estar erradas** → rotular como sugestão e pedir confirmação.
- **Dados incompletos geram margem falsa** → mostrar indicador de "confiança" do cálculo por prato.
- **Taxas de delivery variam** (planos, promoções, cupons) → campos editáveis e padrões claros.
- **Fricção de cadastro de ingredientes** → reaproveitar via nota de compra e catálogo de ingredientes comuns pré-carregado.
- Privacidade/LGPD para fotos e dados financeiros do negócio.

## 13. Roadmap proposto
**Status atual:** já existem a extração de cardápio por foto (com validação e retry), o motor de cálculo de custo/margem/preço sugerido (com testes) e os endpoints `extrair` e `confirmar`. Faltam o agente de ficha técnica, o painel React, o conjunto de avaliação (`evals/`) e o teste com restaurantes reais.

1. **Fase 0 — Descoberta (1 sem):** entrevistar 5–10 donos, validar as dores e testar fotos reais de cardápio com o modelo.
2. **Fase 1 — Protótipo do núcleo (2–3 sem):** foto → pratos → ingredientes → ficha técnica → cálculo de margem (sem polimento).
3. **Fase 2 — MVP (3–4 sem):** semáforo, painel, taxas de delivery, autenticação, mobile-first.
4. **Fase 3 — Extras:** nota de compra por foto, simulador de preços, sugestão de preço ideal.
5. **Fase 4 — Piloto:** 5–10 restaurantes reais, medir métricas, iterar.

## 14. Perguntas em aberto
- Modelo de negócio: assinatura mensal, freemium, cobrança por cardápio analisado?
- Quais plataformas de delivery suportar primeiro (iFood, Rappi, 99Food, WhatsApp próprio)?
- Tem preço diferente no delivery e no balcão? (Impacta o cálculo; assumir campos separados.)
- Vai ter catálogo base de ingredientes e quantidades típicas, ou tudo vem da IA?
- Idioma/região: apenas Brasil (pt-BR, R$) no início?

## 15. Próximos passos imediatos
1. Validar este briefing e fechar as perguntas em aberto prioritárias.
2. Juntar 5–10 fotos reais de cardápios em `evals/fotos/` (com gabarito JSON) e criar o script de avaliação da extração.
3. Implementar o agente de ficha técnica com tool calling e os endpoints correspondentes.
4. Desenhar o fluxo de telas do MVP (foto → revisão → ficha técnica → painel) e iniciar o front React.
