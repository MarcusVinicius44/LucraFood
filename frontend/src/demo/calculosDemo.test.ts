import { describe, expect, it } from 'vitest'
import casosPython from './casos-calculos.json'
import {
  Fracao,
  converterUnidade,
  custoPorUnidade,
  custoPrato,
  decompor,
  diagnosticar,
  margem,
  precoAntigo,
  precoSugerido,
  quantidadeDeMedidas,
  variacaoSobra,
  type ItemCusto,
} from './calculosDemo'

// Cada caso foi calculado pelo backend/cardapio/calculos.py (python manage.py gerar_casos_demo).
// O TypeScript da demo tem de dar exatamente o mesmo valor, centavo por centavo.

type Entrada = Record<string, unknown>
const itens = (lista: unknown): ItemCusto[] =>
  (lista as string[][]).map(([q, preco, qtd]) => [q, custoPorUnidade(preco, qtd)])
const s = (v: unknown) => v as string
const sn = (v: unknown) => (v ?? null) as string | null

function rodar(funcao: string, e: Entrada): Record<string, unknown> {
  switch (funcao) {
    case 'custo_prato':
      return { custo: custoPrato(itens(e.itens), s(e.embalagem), s(e.rendimento)) }
    case 'margem':
      return { margem: margem(s(e.preco), s(e.custo), s(e.taxa), s(e.impostos)) }
    case 'preco_sugerido':
      return { preco: precoSugerido(s(e.custo), s(e.desejada), s(e.taxa), s(e.impostos)) }
    case 'diagnosticar':
      return { ...diagnosticar(s(e.preco), s(e.custo), s(e.taxa), s(e.impostos), sn(e.desejada), sn(e.minima)) }
    case 'decompor':
      return { ...decompor(s(e.preco), itens(e.itens), s(e.embalagem), s(e.rendimento), s(e.taxa), s(e.impostos)) }
    case 'variacao_sobra':
      return variacaoSobra(s(e.preco), itens(e.antes), itens(e.depois), s(e.embalagem), s(e.rendimento), s(e.taxa), s(e.impostos))
    case 'preco_antigo':
      return { antigo: precoAntigo(s(e.atualizado_em), s(e.hoje)) }
    case 'converter_unidade':
      return { quantidade: converterUnidade(s(e.quantidade), s(e.de), s(e.para)) }
    case 'quantidade_de_medidas':
      return { quantidade: quantidadeDeMedidas(s(e.medidas), s(e.por_medida), s(e.de), s(e.para)) }
    default:
      throw new Error(`função sem teste: ${funcao}`)
  }
}

/** Números comparados pelo valor exato (o Python devolve "12" onde o TS devolve "12.00"); o resto, igual. */
function mesmoValor(ts: unknown, py: unknown): boolean {
  if (typeof py === 'string' && typeof ts === 'string' && /^-?\d+(\.\d+)?$/.test(py)) {
    return Fracao.de(ts).comparar(py) === 0
  }
  return ts === py
}

describe('calculosDemo.ts igual ao calculos.py', () => {
  it('tem casos gerados pelo Python', () => {
    expect(casosPython.casos.length).toBeGreaterThanOrEqual(20)
  })

  casosPython.casos.forEach((caso, i) => {
    it(`${i + 1}. ${caso.funcao}`, () => {
      const py = caso.saida as Record<string, unknown>
      if (py.erro) {
        expect(() => rodar(caso.funcao, caso.entrada as Entrada)).toThrow()
        return
      }
      const ts = rodar(caso.funcao, caso.entrada as Entrada)
      for (const [campo, esperado] of Object.entries(py)) {
        expect(mesmoValor(ts[campo], esperado), `${campo}: TS ${String(ts[campo])} x Python ${String(esperado)}`).toBe(true)
      }
    })
  })
})

describe('Fracao', () => {
  it('arredonda meio centavo para cima, longe do zero (ROUND_HALF_UP)', () => {
    expect(Fracao.de('0.005').texto(2)).toBe('0.01')
    expect(Fracao.de('-0.005').texto(2)).toBe('-0.01')
    expect(Fracao.de('0.0049').texto(2)).toBe('0.00')
  })

  it('não perde centavo onde o ponto flutuante perderia', () => {
    // 0.1 + 0.2 em float dá 0.30000000000000004
    expect(Fracao.de('0.1').mais('0.2').comparar('0.3')).toBe(0)
    expect(Fracao.de('10').dividido('3').texto(2)).toBe('3.33')
  })
})
