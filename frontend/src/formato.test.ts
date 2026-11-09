import { describe, expect, it } from 'vitest'
import { chaveDoNome, formatarDiaMes, formatarPct, formatarReais, lerPreco, precoParaCampo, resumoDaFicha } from './formato'

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
