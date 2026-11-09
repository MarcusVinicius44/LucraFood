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
