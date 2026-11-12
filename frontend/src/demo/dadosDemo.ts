// Dados da demo da landing: a lanchonete fictícia, o cadastro fictício e as respostas REAIS da IA
// gravadas pelo comando `python manage.py gravar_demo`. Nada aqui chama a API.
import entrada from './fixtures/entrada-demo.json'
import extracao from './fixtures/gravado-extracao.json'
import fichas from './fixtures/gravado-fichas.json'
import { custoPorUnidade, custoPrato, decompor, diagnosticar, type ContaDemo, type DiagnosticoDemo, type ItemCusto } from './calculosDemo'

export type UnidadeDemo = 'g' | 'ml' | 'un'

export interface IngredienteDemo {
  id: number
  nome: string
  unidade: UnidadeDemo
  preco_embalagem: string
  quantidade_embalagem: string
  atualizado_em: string // AAAA-MM-DD
}

export interface ItemLidoDemo {
  nome_lido: string
  ingrediente: { id: number; nome: string; unidade: string } | null
  quantidade_lida: string | null
  unidade_lida: string | null
  quantidade: string | null
  unidade: string | null
  precisa_confirmar: boolean
  motivos: string[]
  estimativa: string | null
}

export interface PratoDemo {
  nome: string
  descricao: string | null
  categoria: string | null
  preco: string | null
}

export const RESTAURANTE_DEMO = entrada.restaurante
export const INGREDIENTES_DEMO = entrada.ingredientes as IngredienteDemo[]
export const PRATOS_LIDOS: PratoDemo[] = extracao.resposta.pratos.map((p) => ({
  nome: p.nome,
  descricao: p.descricao,
  categoria: p.categoria,
  preco: p.preco === null ? null : Number(p.preco).toFixed(2),
}))
export const FICHAS_GRAVADAS = fichas.fichas as { prato: string; texto: string; itens: ItemLidoDemo[] }[]
export const GRAVACAO = {
  modelo: extracao.modelo,
  data: extracao.gravado_em.slice(0, 10),
  segundos: extracao.segundos,
}

/** "Hoje" da demo fica fixo no dia da gravação, para o aviso de preço antigo não mudar com o tempo. */
export const HOJE_DEMO = GRAVACAO.data

/** Quanto pesa 1 medida caseira, no exemplo (o visitante pode trocar). Valores fictícios. */
export const MEDIDAS_EXEMPLO: Record<number, { medida: string; quantidade: string }> = {
  3: { medida: 'fatia', quantidade: '18' }, // Queijo prato
  16: { medida: 'fatia', quantidade: '20' }, // Queijo muçarela
  4: { medida: 'fatia', quantidade: '15' }, // Cheddar fatiado
  10: { medida: 'colher', quantidade: '15' }, // Maionese
}

export function ingrediente(id: number): IngredienteDemo {
  const i = INGREDIENTES_DEMO.find((x) => x.id === id)
  if (!i) throw new Error(`Ingrediente ${id} fora do cadastro da demo.`)
  return i
}

/** Linha da ficha já conferida: ingrediente do cadastro + quantidade na unidade dele. */
export interface LinhaFicha {
  ingrediente: number
  quantidade: string
}

/** A ficha gravada completada com as medidas de exemplo (o que um dono típico responderia). */
export function fichaExemplo(prato: string): LinhaFicha[] | null {
  const f = FICHAS_GRAVADAS.find((x) => x.prato === prato)
  if (!f) return null
  return f.itens
    .filter((i) => i.ingrediente)
    .map((i) => {
      const id = i.ingrediente!.id
      if (i.quantidade) return { ingrediente: id, quantidade: i.quantidade }
      const medida = MEDIDAS_EXEMPLO[id]
      const vezes = Number(i.quantidade_lida ?? '1')
      return { ingrediente: id, quantidade: String(vezes * Number(medida?.quantidade ?? '0')) }
    })
}

export function itensCusto(linhas: LinhaFicha[], precos: Record<number, string> = {}): ItemCusto[] {
  return linhas.map((l) => {
    const i = ingrediente(l.ingrediente)
    return [l.quantidade, custoPorUnidade(precos[i.id] ?? i.preco_embalagem, i.quantidade_embalagem)]
  })
}

export interface ResultadoDemo {
  diagnostico: DiagnosticoDemo
  conta: ContaDemo
}

/** Diagnóstico do prato com as contas do calculosDemo.ts (cópia testada do calculos.py). */
export function diagnosticoDemo(preco: string, linhas: LinhaFicha[], precos: Record<number, string> = {}): ResultadoDemo {
  const r = RESTAURANTE_DEMO
  const itens = itensCusto(linhas, precos)
  const conta = decompor(preco, itens, 0, 1, r.taxa_delivery_pct, r.impostos_pct)
  // Como diagnostico_do_prato no backend: custo_prato (embalagem 0, ela é ingrediente na demo) -> diagnosticar.
  const custo = custoPrato(itens, 0, 1)
  const diagnostico = diagnosticar(preco, custo, r.taxa_delivery_pct, r.impostos_pct, r.margem_desejada_pct, r.margem_minima_pct)
  return { diagnostico, conta }
}
