// Só formata e lê números para exibir/enviar. Nenhuma conta financeira mora no front:
// custo, margem e preço sugerido vêm prontos do backend (calculos.py).

const reais = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
const percentual = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 })

/** "20.00" (como o DRF devolve decimais) → "R$ 20,00". Nulo vira "—". */
export function formatarReais(valor: string | null | undefined): string {
  if (valor === null || valor === undefined || valor === '') return '—'
  const n = Number(valor)
  // O Intl põe um espaço inquebrável depois do "R$"; troca por espaço comum.
  return Number.isFinite(n) ? reais.format(n).replace(/\s/g, ' ') : '—'
}

/** "19.30" → "19,3%". Percentuais chegam como 0–100. */
export function formatarPct(valor: string | null | undefined): string {
  if (valor === null || valor === undefined || valor === '') return '—'
  const n = Number(valor)
  return Number.isFinite(n) ? `${percentual.format(n)}%` : '—'
}

/** Texto do campo de preço para mostrar ao dono: "20.00" → "20,00". */
export function precoParaCampo(valor: string | null): string {
  return valor === null ? '' : valor.replace('.', ',')
}

export type PrecoLido = { ok: true; valor: string | null } | { ok: false; erro: string }

/**
 * Lê o que o dono digitou no campo de preço e devolve no formato da API ("1234.50").
 * Aceita "20", "20,5", "R$ 20,50", "1.234,56" e "20.50". Vazio = sem preço (null).
 */
export function lerPreco(texto: string): PrecoLido {
  let t = texto.replace(/R\$/gi, '').replace(/\s/g, '')
  if (t === '') return { ok: true, valor: null }
  if (t.includes(',')) {
    // formato brasileiro: ponto é milhar, vírgula é decimal
    t = t.replace(/\./g, '').replace(',', '.')
  }
  if (!/^\d+(\.\d{1,2})?$/.test(t)) {
    return { ok: false, erro: 'Use só números, ex.: 24,90' }
  }
  const [inteiro, decimal = ''] = t.split('.')
  const valor = `${String(Number(inteiro))}.${decimal.padEnd(2, '0')}`
  if (Number(valor) <= 0) return { ok: false, erro: 'O preço precisa ser maior que zero' }
  return { ok: true, valor }
}

/** Mesma regra do backend (views.chave_do_nome): sem diferenciar maiúsculas e espaços. */
export function chaveDoNome(nome: string): string {
  return nome.trim().split(/\s+/).join(' ').toLocaleLowerCase('pt-BR')
}

/** "2026-11-09T16:40:00-03:00" → "09/11". Nulo ou inválido vira null. */
export function formatarDiaMes(iso: string | null | undefined): string | null {
  if (!iso) return null
  const data = new Date(iso)
  if (Number.isNaN(data.getTime())) return null
  return data.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', timeZone: 'America/Sao_Paulo' })
}

/** "ficha com 3 ingredientes · confirmada em 09/11": ajuda o dono a perceber se esqueceu algo. */
export function resumoDaFicha(itens: number, confirmadaEm: string | null): string {
  if (itens === 0) return 'sem ficha técnica'
  const texto = `ficha com ${itens} ${itens === 1 ? 'ingrediente' : 'ingredientes'}`
  const dia = formatarDiaMes(confirmadaEm)
  return dia ? `${texto} · confirmada em ${dia}` : texto
}

export type NumeroLido = { ok: true; valor: string | null } | { ok: false; erro: string }

/**
 * Lê um número digitado em pt-BR e devolve no formato da API ("1500.5").
 * "1,5" → "1.5"; "1.500" (milhar) → "1500"; "1.500,25" → "1500.25"; "0.5" → "0.5".
 * Vazio = null. Não faz conta: só troca o separador.
 */
export function lerNumero(texto: string, casas: number, { permitirZero = false } = {}): NumeroLido {
  let t = texto.replace(/\s/g, '')
  if (t === '') return { ok: true, valor: null }
  if (t.includes(',')) t = t.replace(/\./g, '').replace(',', '.')
  else if (/^\d{1,3}(\.\d{3})+$/.test(t)) t = t.replace(/\./g, '') // "1.500" é mil e quinhentos
  const padrao = new RegExp(String.raw`^\d+(\.\d{1,${casas}})?$`)
  if (!padrao.test(t)) {
    return { ok: false, erro: casas ? `Use só números, até ${casas} casas depois da vírgula` : 'Use só números inteiros' }
  }
  const [inteiro, decimal] = t.split('.')
  const valor = decimal ? `${Number(inteiro)}.${decimal}` : String(Number(inteiro))
  if (!permitirZero && Number(valor) === 0) return { ok: false, erro: 'Precisa ser maior que zero' }
  return { ok: true, valor }
}

/** Quantidade de ficha ou de embalagem (até 3 casas, maior que zero). */
export const lerQuantidade = (texto: string) => lerNumero(texto, 3)

/** Percentual de 0 a 100, até 2 casas ("23%" ou "23,5"). */
export function lerPercentual(texto: string): NumeroLido {
  const lido = lerNumero(texto.replace('%', ''), 2, { permitirZero: true })
  if (lido.ok && lido.valor !== null && Number(lido.valor) > 100) return { ok: false, erro: 'Use de 0 a 100' }
  return lido
}

/** Número do backend ("150.000") para o campo de texto: "150"; "0.500" → "0,5". */
export function numeroParaCampo(valor: string | null | undefined): string {
  if (valor === null || valor === undefined || valor === '') return ''
  const n = Number(valor)
  return Number.isFinite(n) ? n.toLocaleString('pt-BR', { maximumFractionDigits: 3, useGrouping: false }) : ''
}

const NOMES_UNIDADE: Record<string, [string, string]> = {
  g: ['g', 'g'],
  ml: ['ml', 'ml'],
  un: ['unidade', 'unidades'],
}

/** "150.000" + "g" → "150 g"; "2" + "un" → "2 unidades". */
export function formatarQuantidade(valor: string | null, unidade: string | null): string {
  if (valor === null) return '—'
  const n = Number(valor)
  const texto = n.toLocaleString('pt-BR', { maximumFractionDigits: 3 })
  const [um, varios] = NOMES_UNIDADE[unidade ?? ''] ?? [unidade ?? '', unidade ?? '']
  return `${texto} ${n === 1 ? um : varios}`.trim()
}

const reaisUnitario = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
  minimumFractionDigits: 2,
  maximumFractionDigits: 4,
})

/** Custo por grama/ml/unidade: até 4 casas ("0.0420" → "R$ 0,042"), senão o grama vira R$ 0,04. */
export function formatarReaisUnitario(valor: string | null | undefined): string {
  if (valor === null || valor === undefined || valor === '') return '—'
  const n = Number(valor)
  return Number.isFinite(n) ? reaisUnitario.format(n).replace(/\s/g, ' ') : '—'
}
