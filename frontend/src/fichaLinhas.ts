// Linhas da ficha em edição (à mão ou revisando a leitura da IA) e a validação antes de salvar.
// Só confere o que foi digitado; nenhuma conta de custo aqui.
import type { ItemParaSalvar, MedidaParaSalvar, MotivoRevisao, Unidade } from './api'
import { formatarQuantidade, lerQuantidade } from './formato'

/** Uma linha da ficha em edição: veio do cadastro (edição à mão) ou da leitura da IA (revisão). */
export interface LinhaFicha {
  chave: number
  ingrediente: number | null
  quantidade: string // como o dono digita, na unidade do ingrediente escolhido
  nomeLido?: string // como estava escrito no texto
  escrito?: string // quantidade + unidade escritas ("2 fatias"), para referência
  quantidadeLida?: string | null // número escrito ("2" de "2 fatias"), para a conversa
  medidaLida?: string | null // unidade escrita ("fatia"), para a conversa
  unidadeLida?: Unidade | null // unidade-base do que foi escrito (para cadastrar item fora do cadastro)
  motivos: MotivoRevisao[]
  estimativa?: string // de onde veio a quantidade, quando o sistema assumiu algo
  medidaEnsinada?: MedidaParaSalvar // "1 fatia = 18 g" respondido na conversa; gravado ao confirmar
}

/** Medidas ensinadas na conversa que ainda valem: a linha continua com o mesmo ingrediente. */
export function medidasEnsinadas(linhas: LinhaFicha[]): MedidaParaSalvar[] {
  return linhas.flatMap((l) => (l.medidaEnsinada && l.medidaEnsinada.ingrediente === l.ingrediente ? [l.medidaEnsinada] : []))
}

let proxima = 1
export const novaChave = () => proxima++

export type ProblemasFicha = Map<number, { ingrediente?: string; quantidade?: string }>

export function validarLinhas(linhas: LinhaFicha[]): { problemas: ProblemasFicha; itens: ItemParaSalvar[] | null } {
  const problemas: ProblemasFicha = new Map()
  const contagem = new Map<number, number>()
  linhas.forEach((l) => l.ingrediente && contagem.set(l.ingrediente, (contagem.get(l.ingrediente) ?? 0) + 1))
  const itens: ItemParaSalvar[] = []
  for (const l of linhas) {
    const p: { ingrediente?: string; quantidade?: string } = {}
    if (!l.ingrediente) p.ingrediente = 'Escolha o ingrediente'
    else if ((contagem.get(l.ingrediente) ?? 0) > 1) p.ingrediente = 'Repetido: deixe numa linha só'
    const q = lerQuantidade(l.quantidade)
    if (!q.ok) p.quantidade = q.erro
    else if (q.valor === null) p.quantidade = 'Informe a quantidade'
    if (p.ingrediente || p.quantidade) problemas.set(l.chave, p)
    else itens.push({ ingrediente: l.ingrediente!, quantidade: (q as { valor: string }).valor })
  }
  return { problemas, itens: problemas.size ? null : itens }
}

/** "2 fatias", "1,5 kg" — como o dono escreveu, para ele comparar com o que vai salvar. */
export function textoEscrito(quantidade: string | null, unidade: string | null): string | undefined {
  if (quantidade === null && !unidade) return undefined
  if (quantidade === null) return unidade ?? undefined
  // A IA devolve a medida caseira no singular ("fatia"); para 2 fatias, põe no plural.
  const medida = unidade && Number(quantidade) !== 1 ? plural(unidade) : unidade
  return formatarQuantidade(quantidade, medida)
}

const SIGLAS = new Set(['g', 'kg', 'mg', 'ml', 'l', 'un'])

/** Plural simples da primeira palavra: fatia → fatias, colher de sopa → colheres de sopa. */
export function plural(medida: string): string {
  if (SIGLAS.has(medida)) return medida
  const [primeira, ...resto] = medida.split(' ')
  let p = primeira
  if (/[aeiouáéíóú]$/i.test(primeira)) p = primeira + 's'
  else if (/[rz]$/i.test(primeira)) p = primeira + 'es'
  return [p, ...resto].join(' ')
}
