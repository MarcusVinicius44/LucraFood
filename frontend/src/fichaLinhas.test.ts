import { describe, expect, it } from 'vitest'
import { plural, textoEscrito, validarLinhas, type LinhaFicha } from './fichaLinhas'

const linha = (chave: number, ingrediente: number | null, quantidade: string): LinhaFicha => ({
  chave,
  ingrediente,
  quantidade,
  motivos: [],
})

describe('validarLinhas', () => {
  it('devolve os itens prontos para a API quando tudo está certo', () => {
    const r = validarLinhas([linha(1, 10, '150'), linha(2, 11, '1,5')])
    expect(r.problemas.size).toBe(0)
    expect(r.itens).toEqual([
      { ingrediente: 10, quantidade: '150' },
      { ingrediente: 11, quantidade: '1.5' },
    ])
  })
  it('aponta ingrediente faltando, quantidade vazia e repetido', () => {
    const r = validarLinhas([linha(1, null, '10'), linha(2, 5, ''), linha(3, 7, '1'), linha(4, 7, '2')])
    expect(r.itens).toBeNull()
    expect(r.problemas.get(1)?.ingrediente).toBe('Escolha o ingrediente')
    expect(r.problemas.get(2)?.quantidade).toBe('Informe a quantidade')
    expect(r.problemas.get(3)?.ingrediente).toMatch(/Repetido/)
    expect(r.problemas.get(4)?.ingrediente).toMatch(/Repetido/)
  })
})

describe('textoEscrito', () => {
  it('mostra o que o dono escreveu', () => {
    expect(textoEscrito('2', 'fatia')).toBe('2 fatias')
    expect(textoEscrito('1', 'fatia')).toBe('1 fatia')
    expect(textoEscrito('120', 'g')).toBe('120 g')
    expect(textoEscrito(null, 'pitada')).toBe('pitada')
    expect(textoEscrito(null, null)).toBeUndefined()
  })
})

describe('plural', () => {
  it.each([
    ['fatia', 'fatias'],
    ['rodela', 'rodelas'],
    ['colher de sopa', 'colheres de sopa'],
    ['xícara', 'xícaras'],
    ['ml', 'ml'],
  ])('%s → %s', (singular, esperado) => {
    expect(plural(singular)).toBe(esperado)
  })
})
