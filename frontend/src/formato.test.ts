import { describe, expect, it } from 'vitest'
import {
  chaveDoNome,
  formatarDiaMes,
  formatarPct,
  formatarQuantidade,
  formatarReais,
  formatarReaisUnitario,
  lerPercentual,
  lerPreco,
  lerQuantidade,
  numeroParaCampo,
  precoParaCampo,
  resumoDaFicha,
} from './formato'

describe('formatarReais', () => {
  it('formata decimal do DRF em reais', () => {
    expect(formatarReais('20.00')).toBe('R$ 20,00')
    expect(formatarReais('1234.5')).toBe('R$ 1.234,50')
  })
  it('nulo ou inválido vira traço, nunca R$ 0,00', () => {
    expect(formatarReais(null)).toBe('—')
    expect(formatarReais('abc')).toBe('—')
  })
})

describe('formatarPct', () => {
  it('usa vírgula e uma casa', () => {
    expect(formatarPct('19.30')).toBe('19,3%')
    expect(formatarPct('30.00')).toBe('30%')
    expect(formatarPct('-5.25')).toBe('-5,3%')
  })
  it('nulo vira traço', () => {
    expect(formatarPct(null)).toBe('—')
  })
})

describe('lerPreco', () => {
  it.each([
    ['20', '20.00'],
    ['20,5', '20.50'],
    ['R$ 24,90', '24.90'],
    ['1.234,56', '1234.56'],
    ['20.50', '20.50'],
    ['007,10', '7.10'],
  ])('%s → %s', (texto, esperado) => {
    expect(lerPreco(texto)).toEqual({ ok: true, valor: esperado })
  })
  it('vazio é sem preço', () => {
    expect(lerPreco('  ')).toEqual({ ok: true, valor: null })
  })
  it.each(['abc', '20,555', '-3', '0', '0,00'])('recusa %s', (texto) => {
    expect(lerPreco(texto).ok).toBe(false)
  })
})

describe('precoParaCampo', () => {
  it('mostra com vírgula', () => {
    expect(precoParaCampo('20.00')).toBe('20,00')
    expect(precoParaCampo(null)).toBe('')
  })
})

describe('chaveDoNome', () => {
  it('ignora maiúsculas e espaços como o backend', () => {
    expect(chaveDoNome('  X-Burger   Duplo ')).toBe(chaveDoNome('x-burger duplo'))
  })
})

describe('resumoDaFicha', () => {
  it('mostra itens e dia no horário de Brasília', () => {
    expect(resumoDaFicha(3, '2026-11-09T23:30:00-03:00')).toBe('ficha com 3 ingredientes · confirmada em 09/11')
    expect(formatarDiaMes('2026-11-10T01:30:00+00:00')).toBe('09/11') // 22h30 em Brasília
  })
  it('singular, sem data e sem ficha', () => {
    expect(resumoDaFicha(1, null)).toBe('ficha com 1 ingrediente')
    expect(resumoDaFicha(0, null)).toBe('sem ficha técnica')
  })
})

describe('lerQuantidade', () => {
  it.each([
    ['150', '150'],
    ['1,5', '1.5'],
    ['0.5', '0.5'],
    ['1.500', '1500'], // milhar
    ['1.500,25', '1500.25'],
    ['2,125', '2.125'],
  ])('%s → %s', (texto, esperado) => {
    expect(lerQuantidade(texto)).toEqual({ ok: true, valor: esperado })
  })
  it.each(['0', 'abc', '1,2345', '-2'])('recusa %s', (texto) => {
    expect(lerQuantidade(texto).ok).toBe(false)
  })
})

describe('lerPercentual', () => {
  it('aceita 0, vírgula e símbolo', () => {
    expect(lerPercentual('0')).toEqual({ ok: true, valor: '0' })
    expect(lerPercentual('23,5%')).toEqual({ ok: true, valor: '23.5' })
  })
  it('recusa acima de 100', () => {
    expect(lerPercentual('120').ok).toBe(false)
  })
})

describe('quantidades na tela', () => {
  it('mostra sem zeros sobrando', () => {
    expect(numeroParaCampo('150.000')).toBe('150')
    expect(numeroParaCampo('0.500')).toBe('0,5')
    expect(numeroParaCampo('1500.000')).toBe('1500')
    expect(formatarQuantidade('150.000', 'g')).toBe('150 g')
    expect(formatarQuantidade('1.000', 'un')).toBe('1 unidade')
    expect(formatarQuantidade('2.000', 'un')).toBe('2 unidades')
  })
})

describe('formatarReaisUnitario', () => {
  it('mantém até 4 casas para custo por grama', () => {
    expect(formatarReaisUnitario('0.0420')).toBe('R$ 0,042')
    expect(formatarReaisUnitario('1.5000')).toBe('R$ 1,50')
  })
})
