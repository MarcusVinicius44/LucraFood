/**
 * Cópia fiel de backend/cardapio/calculos.py, usada SÓ pela demo da landing (que roda sem back-end).
 * O app real (/app) continua sem nenhuma conta no front: tudo vem pronto do Django.
 *
 * Para não errar centavo com ponto flutuante, os números são frações exatas de BigInt e o
 * arredondamento é o ROUND_HALF_UP do Python (meio centavo sobe, longe do zero).
 * calculosDemo.test.ts exige o mesmo resultado do Python em todos os casos de casos-calculos.json
 * (gerados por `python manage.py gerar_casos_demo`). Mudou calculos.py? Mude aqui e regenere os casos.
 */

export class Fracao {
  readonly n: bigint
  readonly d: bigint

  private constructor(n: bigint, d: bigint) {
    if (d === 0n) throw new Error('Divisão por zero.')
    if (d < 0n) {
      n = -n
      d = -d
    }
    const g = mdc(n < 0n ? -n : n, d)
    this.n = n / g
    this.d = d / g
  }

  /** "15.60", "-2", 37, 0.042 ou outra Fração. Aceita só decimal simples (sem expoente). */
  static de(valor: string | number | bigint | Fracao): Fracao {
    if (valor instanceof Fracao) return valor
    if (typeof valor === 'bigint') return new Fracao(valor, 1n)
    const texto = String(valor).trim()
    const m = /^(-?)(\d*)(?:\.(\d*))?$/.exec(texto)
    if (!m || (m[2] === '' && !m[3])) throw new Error(`Número inválido: ${texto}`)
    const decimais = m[3] ?? ''
    const n = BigInt((m[2] || '0') + decimais) * (m[1] ? -1n : 1n)
    return new Fracao(n, 10n ** BigInt(decimais.length))
  }

  mais(o: Fracao | string | number): Fracao {
    const b = Fracao.de(o)
    return new Fracao(this.n * b.d + b.n * this.d, this.d * b.d)
  }
  menos(o: Fracao | string | number): Fracao {
    const b = Fracao.de(o)
    return new Fracao(this.n * b.d - b.n * this.d, this.d * b.d)
  }
  vezes(o: Fracao | string | number): Fracao {
    const b = Fracao.de(o)
    return new Fracao(this.n * b.n, this.d * b.d)
  }
  dividido(o: Fracao | string | number): Fracao {
    const b = Fracao.de(o)
    if (b.n === 0n) throw new Error('Divisão por zero.')
    return new Fracao(this.n * b.d, this.d * b.n)
  }
  comparar(o: Fracao | string | number): number {
    const b = Fracao.de(o)
    const x = this.n * b.d - b.n * this.d
    return x === 0n ? 0 : x < 0n ? -1 : 1
  }
  menorQue(o: Fracao | string | number): boolean {
    return this.comparar(o) < 0
  }
  /** Arredonda (ROUND_HALF_UP, como o quantize do Python) e devolve texto com `casas` decimais. */
  arredondar(casas: number): Fracao {
    const escala = 10n ** BigInt(casas)
    const negativo = this.n < 0n
    const abs = negativo ? -this.n : this.n
    let q = (abs * escala) / this.d
    const resto = (abs * escala) % this.d
    if (2n * resto >= this.d) q += 1n
    return new Fracao(negativo ? -q : q, escala)
  }
  texto(casas: number): string {
    const r = this.arredondar(casas)
    const escala = 10n ** BigInt(casas)
    const valor = (r.n * escala) / r.d
    const negativo = valor < 0n
    const digitos = (negativo ? -valor : valor).toString().padStart(casas + 1, '0')
    const inteiro = casas ? digitos.slice(0, -casas) : digitos
    const fracao = casas ? `.${digitos.slice(-casas)}` : ''
    return `${negativo ? '-' : ''}${inteiro}${fracao}`
  }
}

function mdc(a: bigint, b: bigint): bigint {
  while (b) [a, b] = [b, a % b]
  return a || 1n
}

type Num = string | number | Fracao
const CEM = Fracao.de(100)
const pct = (v: Num) => Fracao.de(v).dividido(CEM)

export const MARGEM_DESEJADA_PADRAO = '30'
export const MARGEM_MINIMA_PADRAO = '10'

/** Ingrediente.custo_por_unidade: preço da embalagem / quantidade da embalagem. */
export function custoPorUnidade(precoEmbalagem: Num, quantidadeEmbalagem: Num): Fracao {
  return Fracao.de(precoEmbalagem).dividido(quantidadeEmbalagem)
}

/** [quantidade usada, custo por unidade] da receita inteira. */
export type ItemCusto = [Num, Num]

function somaItens(itens: ItemCusto[]): Fracao {
  return itens.reduce((t, [q, c]) => t.mais(Fracao.de(q).vezes(c)), Fracao.de(0))
}

/** Custo de UMA porção: ingredientes / rendimento + embalagem (a embalagem fica fora da divisão). */
export function custoPrato(itens: ItemCusto[], embalagem: Num = 0, rendimento: Num = 1): string {
  const r = Fracao.de(rendimento)
  if (r.comparar(0) <= 0) throw new Error('O rendimento precisa ser maior que zero.')
  return somaItens(itens).dividido(r).mais(embalagem).texto(2)
}

function margemFracao(preco: Num, custo: Num, taxaAppPct: Num, impostosPct: Num): Fracao {
  const p = Fracao.de(preco)
  if (p.comparar(0) <= 0) throw new Error('Preço precisa ser maior que zero.')
  const sobra = p.menos(custo).menos(p.vezes(pct(taxaAppPct).mais(pct(impostosPct))))
  return sobra.dividido(p).vezes(CEM).arredondar(1)
}

/** Margem sobre o preço, em %, depois de custo, taxa do app e impostos (1 casa). */
export function margem(preco: Num, custo: Num, taxaAppPct: Num = 0, impostosPct: Num = 0): string {
  return margemFracao(preco, custo, taxaAppPct, impostosPct).texto(1)
}

export function precoSugerido(custo: Num, margemDesejadaPct: Num, taxaAppPct: Num = 0, impostosPct: Num = 0): string {
  const divisor = Fracao.de(1).menos(pct(taxaAppPct)).menos(pct(impostosPct)).menos(pct(margemDesejadaPct))
  if (divisor.comparar(0) <= 0) throw new Error('Taxas + impostos + margem passam de 100%: não existe preço possível.')
  return Fracao.de(custo).dividido(divisor).texto(2)
}

export type SemaforoDemo = 'verde' | 'amarelo' | 'vermelho'

export interface DiagnosticoDemo {
  custo: string
  margem_balcao: string
  margem_delivery: string
  semaforo: SemaforoDemo
  preco_sugerido_delivery: string | null
}

/** Semáforo pela margem do DELIVERY: vermelho < mínima <= amarelo < desejada <= verde. */
export function diagnosticar(
  preco: Num,
  custo: Num,
  taxaAppPct: Num,
  impostosPct: Num,
  margemDesejadaPct: Num | null = null,
  margemMinimaPct: Num | null = null,
): DiagnosticoDemo {
  const desejada = Fracao.de(margemDesejadaPct ?? MARGEM_DESEJADA_PADRAO)
  const minima = Fracao.de(margemMinimaPct ?? MARGEM_MINIMA_PADRAO)
  if (minima.comparar(desejada) > 0) throw new Error('A margem mínima não pode ser maior que a margem desejada.')
  const mBalcao = margemFracao(preco, custo, 0, impostosPct)
  const mDelivery = margemFracao(preco, custo, taxaAppPct, impostosPct)
  const semaforo: SemaforoDemo = mDelivery.menorQue(minima) ? 'vermelho' : mDelivery.menorQue(desejada) ? 'amarelo' : 'verde'
  return {
    custo: Fracao.de(custo).texto(2),
    margem_balcao: mBalcao.texto(1),
    margem_delivery: mDelivery.texto(1),
    semaforo,
    preco_sugerido_delivery: semaforo === 'verde' ? null : precoSugerido(custo, desejada, taxaAppPct, impostosPct),
  }
}

/** A conta de um pedido em reais: preço − ingredientes − embalagem − impostos − taxa do app = sobra. */
export interface ContaDemo {
  preco: string
  ingredientes: string
  embalagem: string
  impostos: string
  taxa_app: string
  sobra: string
}

export function decompor(
  preco: Num,
  itens: ItemCusto[],
  embalagem: Num = 0,
  rendimento: Num = 1,
  taxaAppPct: Num = 0,
  impostosPct: Num = 0,
): ContaDemo {
  const p = Fracao.de(preco)
  if (p.comparar(0) <= 0) throw new Error('Preço precisa ser maior que zero.')
  const r = Fracao.de(rendimento)
  if (r.comparar(0) <= 0) throw new Error('O rendimento precisa ser maior que zero.')
  const ingredientes = somaItens(itens).dividido(r).arredondar(2)
  const emb = Fracao.de(embalagem).arredondar(2)
  const impostos = p.vezes(pct(impostosPct)).arredondar(2)
  const taxa = p.vezes(pct(taxaAppPct)).arredondar(2)
  const sobra = p.menos(ingredientes).menos(emb).menos(impostos).menos(taxa)
  return {
    preco: p.texto(2),
    ingredientes: ingredientes.texto(2),
    embalagem: emb.texto(2),
    impostos: impostos.texto(2),
    taxa_app: taxa.texto(2),
    sobra: sobra.texto(2),
  }
}

/** Sobra do delivery antes e depois de um ingrediente mudar de preço ("Em desenvolvimento" na demo). */
export function variacaoSobra(
  preco: Num,
  itensAntes: ItemCusto[],
  itensDepois: ItemCusto[],
  embalagem: Num = 0,
  rendimento: Num = 1,
  taxaAppPct: Num = 0,
  impostosPct: Num = 0,
): { antes: string; depois: string; diferenca: string } {
  const antes = decompor(preco, itensAntes, embalagem, rendimento, taxaAppPct, impostosPct).sobra
  const depois = decompor(preco, itensDepois, embalagem, rendimento, taxaAppPct, impostosPct).sobra
  return { antes, depois, diferenca: Fracao.de(depois).menos(antes).texto(2) }
}

export const PRECO_ANTIGO_DIAS = 30

/** Dias entre duas datas "AAAA-MM-DD" (calendário, sem fuso). */
export function diasEntre(de: string, ate: string): number {
  const dia = (s: string) => {
    const [a, m, d] = s.split('-').map(Number)
    return Date.UTC(a, m - 1, d) / 86_400_000
  }
  return dia(ate) - dia(de)
}

/** Preço sem atualizar há MAIS de 30 dias: a conta pode estar desatualizada ("Em desenvolvimento"). */
export function precoAntigo(atualizadoEm: string, hoje: string, limiteDias = PRECO_ANTIGO_DIAS): boolean {
  return diasEntre(atualizadoEm, hoje) > limiteDias
}

const FATORES: Record<string, [string, string]> = {
  mg: ['g', '0.001'],
  g: ['g', '1'],
  kg: ['g', '1000'],
  ml: ['ml', '1'],
  l: ['ml', '1000'],
  un: ['un', '1'],
}

/** 0,2 kg -> "200.000" g (3 casas). Erro se não houver conversão exata (ex.: fatia). */
export function converterUnidade(quantidade: Num, de: string, para: string): string {
  const f = FATORES[de]
  if (!f) throw new Error(`Unidade sem conversão exata: ${de}.`)
  if (f[0] !== para) throw new Error(`Não dá para converter ${de} em ${para}.`)
  return Fracao.de(quantidade).vezes(f[1]).texto(3)
}

/** 2 fatias de 18 g -> "36.000" g. */
export function quantidadeDeMedidas(medidas: Num, porMedida: Num, de: string, para: string): string {
  const m = Fracao.de(medidas)
  const p = Fracao.de(porMedida)
  if (m.comparar(0) <= 0 || p.comparar(0) <= 0) throw new Error('Quantidades precisam ser maiores que zero.')
  return converterUnidade(m.vezes(p), de, para)
}
