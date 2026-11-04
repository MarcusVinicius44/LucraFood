# LucraFood — Agentes e Skills

Dois grupos distintos:
- **A. Ferramentas de desenvolvimento** (Claude Code): agentes e skills que usamos para *construir* o projeto.
- **B. Agentes do produto** (dentro do app): a IA que o dono do restaurante usa. Construídos sobre o Groq (SDK `openai`).

---

## A. Desenvolvimento (Claude Code)

### A1. Agentes (subagentes)
| Agente | Quando usar no LucraFood |
|---|---|
| **Plan** | Desenhar a arquitetura, o modelo de dados e o plano de cada fase do roadmap antes de codar. |
| **Explore** | Buscar no código (ex.: onde vive a regra de margem, onde o semáforo é calculado) quando o projeto crescer. |
| **general-purpose** | Pesquisas abertas e tarefas de várias etapas (ex.: levantar as taxas atuais de iFood/Rappi). |
| **claude-code-guide** | Dúvidas sobre o próprio Claude Code (hooks, skills, subagentes, permissões). |
| **claude** | Agente padrão para o que não se encaixa nos demais. |

Regra: só acionar subagente quando valer a pena (tarefa grande e independente). Tarefas pequenas ficam na sessão principal.

### A2. Skills
**Essenciais (usar desde o início):**
| Skill | Uso |
|---|---|
| `init` | Gerar o `CLAUDE.md` com convenções, comandos e regras de negócio do projeto. |
| ~~`claude-api`~~ | **Não se aplica agora:** o produto usa Groq via SDK `openai`, não a API da Anthropic. Só entra se o provedor for trocado para Claude. |
| `artifact-design` / `dataviz` | Desenhar o painel de diagnóstico (cards de custo/margem, semáforo, ranking de pratos) com gráficos consistentes e acessíveis. |
| `run` | Subir o app e confirmar que cada mudança funciona de verdade, não só nos testes. |

**Qualidade (a cada entrega):**
| Skill | Uso |
|---|---|
| `code-review` | Revisar o diff antes de cada merge; foco nas contas de margem, onde um erro vira número financeiro errado. |
| `simplify` | Limpar e reduzir duplicação depois de uma feature pronta. |
| `security-review` | Revisar upload de imagens, autenticação e dados financeiros dos restaurantes (LGPD). |

**Testes e acabamento:**
| Skill / ferramenta | Uso |
|---|---|
| `claude-in-chrome` | Testar o fluxo no navegador (upload de foto, revisão, ficha técnica, painel) e checar console/rede. |
| Figma (MCP) | Se o design for feito no Figma: ler o design e implementar, ou gerar telas a partir do código. |
| `anthropic-skills:xlsx` / `pdf` | Futuro: exportar o diagnóstico em planilha ou PDF para o dono. |
| `anthropic-skills:docs` | Documentos de produto (specs, relatórios de piloto). |

**Configuração e automação:**
| Skill | Uso |
|---|---|
| `update-config` / `fewer-permission-prompts` | Ajustar permissões e hooks (ex.: rodar testes/lint automaticamente). |
| `loop` / `schedule` | Rotinas recorrentes (ex.: checar qualidade da leitura de cardápios na fase de piloto). |
| `anthropic-skills:skill-creator` | Criar skills próprias do projeto (abaixo). |

### A3. Skills e subagentes próprios (a criar)
- Skill `lucrafood-margem`: regras de cálculo (custo, margem balcão/delivery, semáforo: verde ≥ desejada [padrão 30%], vermelho < mínima [padrão 10%]) como fonte única de verdade.
- Skill `lucrafood-prompts`: padrões dos prompts e esquemas JSON dos agentes do produto.
- Subagente `revisor-financeiro`: confere a matemática e a conversão de unidades (g↔kg, ml↔L).
- Subagente `avaliador-cardapio`: roda um conjunto fixo de fotos de cardápio e mede a precisão da leitura.

---

## B. Agentes do produto (dentro do LucraFood)

Todos usam o Groq (SDK `openai`, modelo `qwen/qwen3.8-27b` com visão, JSON e tool calling), saída validada com Pydantic e confirmação humana antes de gravar valores financeiros. O Agente 1 já existe em `backend/cardapio/ia/extracao.py`.

| # | Agente | Entrada | Saída | Ferramentas (tool use) |
|---|---|---|---|---|
| 1 | **Leitor de Cardápio** | Foto do cardápio | Lista de pratos: nome, descrição, preço | `salvar_pratos` (após revisão do dono) |
| 2 | **Leitor de Nota de Compra** *(fase 2)* | Foto da nota | Itens, quantidades e preços unitários | `atualizar_preco_ingrediente` |
| 3 | **Ficha Técnica Conversada** | Prato + conversa curta | Ingredientes e quantidades por prato | `buscar_quantidade_tipica`, `salvar_ficha_item` |
| 4 | **Analista de Margem** | Pratos, custos, taxas | Explicação em linguagem simples do semáforo | `calcular_margem` (determinística, **não** é feita pelo LLM) |

Princípios:
- **A conta é código, não IA.** O LLM extrai e conversa; o cálculo de custo e margem roda em funções determinísticas e testadas.
- **A IA sugere, o dono confirma.** Nada financeiro é salvo sem confirmação.
- **Sinalizar incerteza.** Quantidades sugeridas aparecem como "sugestão" até o dono confirmar.

---

## C. Ordem de uso por fase do roadmap
1. **Já feito:** `init` (CLAUDE.md), Leitor de Cardápio, motor de cálculo.
2. **Fase 2 (MVP):** `Plan` (agente de ficha técnica com tool calling) → `run` → `dataviz`/`artifact-design` (painel React) → `claude-in-chrome` (testes) → `code-review` + `simplify`.
3. **Antes do piloto:** `security-review`, skills próprias (A3), `avaliador-cardapio`.
4. **Fase 3+:** Leitor de Nota, `xlsx`/`pdf` para exportação, `schedule` para monitoramento.
