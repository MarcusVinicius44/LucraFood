# Avaliação da IA no LucraFood

Histórico completo das medições. Cada rodada chama a API de verdade (gasta a cota do provedor) e a saída fica guardada em `evals/*/resultados/`. O resumo está no [README](../README.md#resultados-medidos).

## Extração do cardápio por foto

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

### Foto 09: foto de celular apontada para a tela (10/11/2026)

Primeira foto tirada no celular do dono (`cardapio_09.jpeg`): um cardápio aberto no monitor, fotografado de lado, com reflexo e o padrão de linhas da tela. Chegou com 900 × 1600 px e 208 KB (o aplicativo de mensagens já tinha reduzido), então foi enviada como está, sem a recompressão do navegador. Gabarito com 17 pratos, escrito por IA (Claude) olhando a foto e revisado pelo dono em 10/11/2026.

| Data | Provedor e modelo | Pratos | Preços certos | Tempo |
|---|---|---|---|---|
| 10/11/2026 | Gemini `gemini-3.5-flash-lite` | **17 de 17** | **17 de 17** | 51 s (2 recusas 503 antes de responder) |

Limitações desta foto como teste: todos os preços são R$ 20, então ela mede pouco a leitura de dígitos, e não é o caso de alta resolução (4000 px reduzida para 2400 px), que continua sem medição. Saída em [`evals/cardapios/resultados/2026-11-10_foto09_celular.txt`](../evals/cardapios/resultados/2026-11-10_foto09_celular.txt).

## Foto reduzida pelo navegador (JPEG)

O frontend envia a foto como está se ela tiver até 4 MB e for JPG, PNG ou WEBP. Só a foto maior (comum em celular) ou em outro formato (HEIC) é reduzida para 2400 px no lado maior e recomprimida em JPEG. Para saber se essa recompressão atrapalha, as 8 fotos foram convertidas do jeito que o navegador faz (`evals/cardapios/gerar_jpeg.py`) e avaliadas. Como elas têm menos de 1000 px, nenhuma foi reduzida: **o teste mede só a troca de PNG por JPEG**. Gemini `gemini-3.5-flash-lite`, 09/11/2026, saídas em `evals/cardapios/resultados/`.

| Rodada (8 fotos) | Pratos | Preços certos | Onde errou |
|---|---|---|---|
| PNG original | 251 de 254 | **251 de 251** | (só os caldinhos de sempre) |
| JPEG 85%, rodada 1 | 251 de 254 | 218 de 251 | foto 06: 32 pizzas (41→47, 51→53); foto 05: 189→169 |
| JPEG 85%, rodada 2 | 251 de 254 | 250 de 251 | foto 05: 189→169 |
| JPEG 92% | 244 de 248 (foto 07 deu *timeout* do provedor) | 212 de 244 | foto 06: 32 pizzas |

Repetindo só a foto 06 (preços escritos à mão, foto com 513 px de largura): **PNG acertou 7 de 7 rodadas; JPEG errou as 32 pizzas em 4 de 8** (85%: 1 de 4; 92%: 3 de 4, mais 1 *timeout*). Os valores 47 e 53 não existem na foto.

- **Conclusão:** nessas fotos pequenas, recomprimir em JPEG piora a leitura de dígitos manuscritos, e subir a qualidade de 85% para 92% não resolveu. Por isso o app só recomprime quando precisa (foto acima de 4 MB ou HEIC).
- **O que ainda não foi medido:** o caso real da redução, foto de celular com 4000 px ou mais reduzida para 2400 px. Nela cada dígito tem 4 a 5 vezes mais pixels do que nas fotos de avaliação, então o efeito deve ser menor, mas falta conferir com fotos de cardápio em alta resolução e gabarito.

## Ficha técnica por texto

`python manage.py avaliar_ficha` sobre as 10 frases de `evals/fichas/` (42 ingredientes esperados, cadastro fictício de 21 itens), cada uma cobrindo um caso: sinônimo, pão sem número, kg e litro com vírgula, concha/xícara/fio, ingrediente fora do cadastro, queijo parecido mas diferente, erro de digitação e texto com ruído.

| Data | Gabarito | Provedor e modelo | Ingrediente certo | Quantidade certa | Ligados ao ingrediente errado |
|---|---|---|---|---|---|
| 08/11/2026 | rascunho da IA | Gemini `gemini-3.5-flash-lite` | 40 de 42 (95,2%) | 33 de 33 (só itens do cadastro) | 0 |
| 08/11/2026 | revisado em f06, f07 e f09 | Gemini `gemini-3.5-flash-lite` | 42 de 42 | 33 de 33 (só itens do cadastro) | 0 |
| 08/11/2026 | revisado pelo dono (todas as frases) | Gemini `gemini-3.5-flash-lite` | 40 a 42 de 42 (5 rodadas: 42, 42, 41, 41, 40) | 100% em todas as rodadas (40 a 42 itens, inclusive fora do cadastro) | 0 ou 1 |
| 08/11/2026 | revisado + Cheddar e Parmesão no cadastro | Gemini `gemini-3.5-flash-lite` | **42 de 42 nas 5 rodadas** | **42 de 42 nas 5 rodadas** | **0** |

Cada rodada faz 10 chamadas (~1 s por frase; algumas rodadas levaram ~70 s por esperarem 503 do Gemini). **O prompt não mudou em nenhuma dessas rodadas**: mudaram o gabarito, a métrica e um defeito do Python. O motivo de cada ajuste:

1. **"queijo" genérico vai para revisão** (f07 e f09, depois da primeira rodada). A IA deixou "queijo" sem ingrediente e o rascunho esperava "Queijo prato". O dono concordou com a IA: um custo errado é pior que uma pergunta a mais.
2. **f09 reescrita** porque era ambígua ("frango empanado na farinha (uns 30 g)": os 30 g podiam ser do frango ou da farinha), e frase ambígua não mede acerto.
3. **Regra dos nomes genéricos** (revisão completa): só fica sem ingrediente o nome genérico de produto com variações de preço bem diferentes (ex.: queijo). Genéricos com um candidato óbvio (pão, leite, óleo, farinha, frango) são ligados, como o gabarito já esperava.
4. **Item fora do cadastro guarda a quantidade escrita.** "150 g de mussarela" deve voltar 150 g, para o dono cadastrar o ingrediente já sabendo quanto usa. O Python apagava essa quantidade quando o ingrediente ficava `null`. Isso foi corrigido em [`9b4c657`](https://github.com/MarcusVinicius44/LucraFood/commit/9b4c657), e esses itens passaram a contar na métrica de quantidade, conferindo também a unidade. Pela mesma regra, "2 cenouras" (f05) passou a esperar 2 un. Medida informal (concha, xícara, fio, bolas) continua sem quantidade.

**Variação entre rodadas** (mesmo prompt, mesmo gabarito), toda na f07 ("2 ovos, um fio de óleo, 50 g de queijo, sal e pimenta"): em 2 de 5 rodadas a IA ligou "queijo" a Queijo prato, e uma vez juntou "sal e pimenta" num item só. Uma rodada de 41 não teve a saída guardada, então o item que faltou nela é desconhecido. O cadastro de avaliação tinha um único queijo, o que deixava esse caso no limite da regra 3.

5. **Cheddar e Parmesão no cadastro de avaliação**, com preços bem diferentes do Queijo prato (R$ 65 e R$ 130/kg contra R$ 45/kg), para "queijo" ser de fato genérico como a regra 3 descreve. Os preços só documentam a regra: a IA recebe apenas id, nome e unidade. Com isso, a f07 ficou estável e as 5 rodadas deram 42 de 42 nos ingredientes e nas quantidades. A saída completa de cada rodada está em [`evals/fichas/resultados/`](../evals/fichas/resultados/).

## Regra C e motivos de revisão (10/11/2026)

**Regra C:** quando a IA liga o que o dono escreveu a um ingrediente de nome diferente, o item continua ligado, mas pode vir marcado para conferir (`nome_diferente`). A decisão é do Python (`nome_confere` em `ia/ficha.py`), comparando palavras sem acento, maiúsculas, plural simples e palavras como "de". **O prompt não mudou.**

**Motivos de revisão:** o gabarito ganhou o campo opcional `confirmar` (true/false) e o comando mede se `precisa_confirmar` saiu como esperado. As 10 frases revisadas não foram alteradas; as frases ambíguas de propósito ficam em `evals/fichas/frases_revisao.json`, escritas por IA e **revisadas pelo dono em 10/11/2026** (depois das rodadas abaixo; nenhuma frase mudou na revisão).

A regra teve duas versões no mesmo dia:

| Versão | Quando marca `nome_diferente` | `frases.json` (revisado): ingrediente / quantidade | Itens marcados em `frases.json` | `frases_revisao.json`: conferência certa | Saídas |
|---|---|---|---|---|---|
| sem a regra (antes) | nunca | 42/42 e 42/42 | 15 de 42 | (não existia) | contado na saída da 1ª versão, sem o motivo novo |
| 1ª: estrita | sempre que o nome lido não contém todas as palavras do cadastro | 42/42 e 42/42 | 24 de 42 | 18 de 18 (6 frases) | `2026-11-10_regra_c_frases.txt`, `2026-11-10_regra_c_revisao_r1.txt` |
| **2ª: branda (atual)** | sinônimo, erro de digitação ou nome curto com mais de um candidato no cadastro | **42/42 e 42/42** | **17 de 42** | **21 de 21** (7 frases) | `2026-11-10_regra_c_branda_frases.txt`, `2026-11-10_regra_c_branda_revisao.txt` |

Uma rodada de cada, Gemini `gemini-3.5-flash-lite`. Saídas em [`evals/fichas/resultados/`](../evals/fichas/resultados/).

- **Por que a versão estrita foi trocada:** ela marcava 9 itens a mais, quase todos nomes curtos com um único candidato ("batata" → Batata congelada, "farinha" → Farinha de trigo, "leite" → Leite integral). Com mais da metade da ficha destacada, o dono tende a marcar "Conferi" sem ler, e o aviso perde o valor justo onde importa (medida caseira, unidade errada).
- **O que a branda marca a mais que antes:** só "hambúrguer" → Blend bovino (sinônimo) e "qeijo prato" (erro de digitação).
- **Na tela, dois níveis:** "confira o nome" aparece como aviso leve (ⓘ, fundo neutro), porque o item já está completo; motivos que pedem para preencher algo continuam com o aviso amarelo (⚠). Os dois entram em "Conferi os itens destacados".
- **Mudanças no rascunho para a regra branda:** r01 ("leite", um único leite no cadastro) e r05 ("batata") passaram a esperar `confirmar: false`; entrou a r07 (erro de digitação "aroz" e "hamburguer" sem acento → Blend bovino).
- **O que essa medição prova:** se a IA lê o ingrediente e a unidade certos, os motivos vêm do Python e são determinísticos (testados em `tests_ficha.py`). O resultado confirma isso na prática; não mede se o dono lê os avisos, o que só o teste com restaurantes vai mostrar.
- **Não testado com dados reais:** nome curto com vários candidatos (o cadastro de avaliação tem um único leite; está só nos testes unitários, para não mexer no cadastro revisado).

## Ficha em conversa: leitura das respostas (10/11/2026)

Na ficha em conversa, o Python escolhe a pergunta ("Quanto dá mais ou menos 1 fatia de Queijo prato, em gramas?") e faz a conta; a IA só lê a resposta do dono e devolve o número e a unidade como foram ditos, ou "não sabe" / "não entendi" (`ia/conversa.py`). `python manage.py avaliar_conversa` mede só essa leitura, com 14 respostas em `evals/fichas/respostas.json` (escritas por IA e revisadas pelo dono em 10/11/2026). A conta (2 × 18 g = 36 g, kg → g) é testada sem API em `tests_conversa.py`.

| Data | Provedor e modelo | Respostas lidas certo | Saída |
|---|---|---|---|
| 10/11/2026 | Gemini `gemini-3.5-flash-lite` | 13 de 14 | [`2026-11-10_conversa_r1.txt`](../evals/fichas/resultados/2026-11-10_conversa_r1.txt) |

- **O único erro (c02):** a resposta "uma colher de sopa mais ou menos" voltou como unidade "colher de sopa" sem a quantidade 1. Na tela o resultado é o mesmo do esperado (o Python recusa medida caseira e pede o valor em ml), mas a leitura não bate com o gabarito. O dono decidiu manter como erro: ele disse "uma", e o gabarito registra o que foi dito (o 1 passa a importar se a resposta um dia aceitar uma medida lembrada).
- **Primeira medição do prompt novo:** serve de referência para qualquer mudança nele.
- **Teste no navegador** (banco temporário): a receita "pão, 150 de blend bovino, 2 fatias de queijo prato e 30 g de óleo" gerou 3 perguntas, respondidas com "isso mesmo" (150 g), "cada fatia uns 18 gramas" (36 g) e "uns 33 ml"; a resposta "uma colher" para o óleo foi recusada pedindo ml.

