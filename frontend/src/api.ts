// Todas as chamadas ao backend Django. Os tipos espelham as respostas da API.
// Decimais chegam como texto ("20.00"), do jeito que o DRF devolve, para não perder centavos.

export type Semaforo = 'verde' | 'amarelo' | 'vermelho'
export type Pendencia = 'sem_preco' | 'sem_ficha' | 'configuracao'

export interface PratoExtraido {
  nome: string
  descricao: string | null
  categoria: string | null
  preco: string | null
}

export interface CardapioExtraido {
  pratos: PratoExtraido[]
}

export interface Restaurante {
  id: number
  nome: string
  taxa_delivery_pct: string
  impostos_pct: string
  margem_desejada_pct: string
  margem_minima_pct: string
}

/** Resultado de calculos.diagnosticar (ou a pendência que impede o semáforo). */
export interface Diagnostico {
  semaforo: Semaforo | null
  pendente: Pendencia | null
  mensagem: string | null
  custo: string | null // custo da porção: ingredientes / rendimento + embalagem
  margem_balcao_pct: string | null
  margem_delivery_pct: string | null
  preco_sugerido_delivery: string | null
}

export interface PratoPainel extends Diagnostico {
  id: number
  nome: string
  categoria: string
  preco_venda: string | null
  custo_embalagem: string | null
  rendimento: string | null
  ficha_itens: number
  ficha_confirmada_em: string | null // ISO com fuso (ex.: 2026-11-09T16:40:00-03:00)
}

export type Unidade = 'g' | 'ml' | 'un'

export interface Ingrediente {
  id: number
  nome: string
  unidade: Unidade
  preco_embalagem: string
  quantidade_embalagem: string
  custo_por_unidade: string // só exibição (4 casas)
}

export type IngredienteNovo = Pick<Ingrediente, 'nome' | 'unidade' | 'preco_embalagem' | 'quantidade_embalagem'>

export interface ItemFicha {
  ingrediente: number
  nome: string
  unidade: Unidade
  quantidade: string // na unidade do cadastro
  custo: string
}

export interface FichaDoPrato {
  prato: number
  nome: string
  preco_venda: string | null
  custo_embalagem: string
  rendimento: string
  custo_receita: string // só ingredientes, receita inteira
  ficha_itens: number
  ficha_confirmada_em: string | null
  itens: ItemFicha[]
  diagnostico: Diagnostico
}

export interface PratoDados {
  id: number
  nome: string
  categoria: string
  preco_venda: string | null
  custo_embalagem: string
  rendimento: string
}

export type MotivoRevisao =
  | 'sem_ingrediente'
  | 'sem_quantidade'
  | 'sem_unidade'
  | 'unidade_informal'
  | 'unidade_incompativel'
  | 'ingrediente_repetido'
  | 'nome_diferente'

/** Item lido pela IA no texto da receita, já conferido pelo Python (ia/ficha.py). */
export interface ItemLidoTexto {
  nome_lido: string
  ingrediente: { id: number; nome: string; unidade: Unidade } | null
  quantidade_lida: string | null
  unidade_lida: string | null
  quantidade: string | null // na unidade de `unidade`
  unidade: Unidade | null
  precisa_confirmar: boolean
  motivos: MotivoRevisao[]
}

export interface FichaLidaTexto {
  prato: number
  nome: string
  precisa_confirmar: boolean
  itens: ItemLidoTexto[]
}

export type ItemParaSalvar = { ingrediente: number; quantidade: string }

export interface RespostaConfirmar {
  restaurante_id: number
  pratos_salvos: number
}

/** Erro vindo da API, com a mensagem pronta para mostrar ao dono. */
export class ErroApi extends Error {
  status: number
  codigo?: string
  dados: Record<string, unknown>

  constructor(status: number, mensagem: string, dados: Record<string, unknown> = {}) {
    super(mensagem)
    this.status = status
    this.dados = dados
    this.codigo = typeof dados.codigo === 'string' ? dados.codigo : undefined
  }
}

const MENSAGENS_POR_STATUS: Record<number, string> = {
  404: 'Não encontrei esse registro.',
  429: 'Limite de uso da IA atingido. Tente de novo em alguns minutos.',
  502: 'A IA respondeu algo que não deu para entender. Tente de novo.',
  503: 'O serviço de IA está sobrecarregado. Tente de novo em alguns minutos.',
}

/**
 * Junta as mensagens que o backend devolve. Nossas views usam {"erro": "..."};
 * os serializers do DRF devolvem {"campo": ["mensagem", ...]}.
 */
export function mensagemDoErro(status: number, dados: unknown): string {
  // O 404 padrão do DRF vem em inglês ("No X matches the given query.").
  if (status === 404) return MENSAGENS_POR_STATUS[404]
  if (dados && typeof dados === 'object') {
    const d = dados as Record<string, unknown>
    if (typeof d.erro === 'string') return d.erro
    if (typeof d.detail === 'string') return d.detail
    const partes = Object.values(d)
      .flatMap((v) => (Array.isArray(v) ? v : [v]))
      .filter((v): v is string => typeof v === 'string')
    if (partes.length) return partes.join(' ')
  }
  return MENSAGENS_POR_STATUS[status] ?? `Algo deu errado no servidor (erro ${status}).`
}

async function pedir<T>(url: string, init?: RequestInit): Promise<T> {
  let resposta: Response
  try {
    resposta = await fetch(url, init)
  } catch {
    throw new ErroApi(0, 'Não consegui falar com o servidor. Confira a internet e se o backend está ligado.')
  }
  const dados = await resposta.json().catch(() => ({}))
  if (!resposta.ok) {
    throw new ErroApi(resposta.status, mensagemDoErro(resposta.status, dados), dados)
  }
  return dados as T
}

function json(metodo: string, corpo: unknown): RequestInit {
  return { method: metodo, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(corpo) }
}

/** Foto → pratos lidos pela IA. Não salva nada. */
export function extrairCardapio(imagem: Blob, nomeArquivo: string): Promise<CardapioExtraido> {
  const form = new FormData()
  form.append('imagem', imagem, nomeArquivo)
  return pedir('/api/cardapio/extrair/', { method: 'POST', body: form })
}

/** Grava a lista conferida pelo dono. 409 se algum prato já existe no restaurante. */
export function confirmarCardapio(restaurante: string, pratos: PratoExtraido[]): Promise<RespostaConfirmar> {
  return pedir('/api/cardapio/confirmar/', json('POST', { restaurante, pratos }))
}

export function buscarRestaurante(id: number): Promise<Restaurante> {
  return pedir(`/api/restaurantes/${id}/`)
}

export function listarPratos(restauranteId: number): Promise<PratoPainel[]> {
  return pedir(`/api/restaurantes/${restauranteId}/pratos/`)
}

export function atualizarRestaurante(id: number, campos: Partial<Omit<Restaurante, 'id'>>): Promise<Restaurante> {
  return pedir(`/api/restaurantes/${id}/`, json('PATCH', campos))
}

// --- Ingredientes ---------------------------------------------------------

export function listarIngredientes(restauranteId: number): Promise<Ingrediente[]> {
  return pedir(`/api/restaurantes/${restauranteId}/ingredientes/`)
}

export function criarIngrediente(restauranteId: number, dados: IngredienteNovo): Promise<Ingrediente> {
  return pedir(`/api/restaurantes/${restauranteId}/ingredientes/`, json('POST', dados))
}

export function atualizarIngrediente(id: number, dados: Partial<IngredienteNovo>): Promise<Ingrediente> {
  return pedir(`/api/ingredientes/${id}/`, json('PATCH', dados))
}

/** 409 se o ingrediente está em alguma ficha (a resposta traz os pratos). */
export function apagarIngrediente(id: number): Promise<void> {
  return pedir(`/api/ingredientes/${id}/`, { method: 'DELETE' })
}

// --- Prato e ficha --------------------------------------------------------

export function buscarPrato(id: number): Promise<PratoDados> {
  return pedir(`/api/pratos/${id}/`)
}

export function atualizarPrato(
  id: number,
  campos: Partial<Pick<PratoDados, 'preco_venda' | 'custo_embalagem' | 'rendimento'>>,
): Promise<PratoDados> {
  return pedir(`/api/pratos/${id}/`, json('PATCH', campos))
}

export function buscarFicha(pratoId: number): Promise<FichaDoPrato> {
  return pedir(`/api/pratos/${pratoId}/ficha/`)
}

/** Substitui a ficha inteira (lista vazia limpa). */
export function salvarFicha(pratoId: number, itens: ItemParaSalvar[]): Promise<FichaDoPrato> {
  return pedir(`/api/pratos/${pratoId}/ficha/`, json('PUT', { itens }))
}

/** Texto da receita → itens lidos pela IA para o dono revisar. Não salva. */
export function lerFichaTexto(pratoId: number, texto: string): Promise<FichaLidaTexto> {
  return pedir(`/api/pratos/${pratoId}/ficha/extrair/`, json('POST', { texto }))
}

export function confirmarFichaTexto(pratoId: number, itens: ItemParaSalvar[]): Promise<FichaDoPrato> {
  return pedir(`/api/pratos/${pratoId}/ficha/confirmar/`, json('POST', { itens }))
}
