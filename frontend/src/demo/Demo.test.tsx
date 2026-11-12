// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Demo from './Demo'

// O fluxo inteiro da demo, do começo ao fim, sem back-end: nenhuma chamada de rede pode acontecer.
describe('demo da landing', () => {
  const fetchEspiao = vi.fn()

  beforeEach(() => {
    vi.stubGlobal('fetch', fetchEspiao)
  })
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
    fetchEspiao.mockReset()
  })

  it('foto → revisão → painel → receita → diagnóstico → simulador → recomeçar, sem chamar a API', async () => {
    render(<Demo atrasoMs={0} />)

    // 1. Foto
    fireEvent.click(screen.getByRole('button', { name: 'Ler cardápio' }))

    // 2. Revisão: 11 pratos gravados; o visitante corrige um preço
    await screen.findByText('Confira os pratos que a IA leu')
    expect(screen.getAllByLabelText('Preço (R$)')).toHaveLength(11)
    expect(screen.getAllByText(/Resultado gravado de uma leitura real/).length).toBeGreaterThan(0)
    fireEvent.change(screen.getByDisplayValue('Água Mineral').closest('li')!.querySelector('input[inputmode="decimal"]')!, {
      target: { value: '4,50' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar e ver o painel' }))

    // 3. Painel: sem receita, nenhum número
    await screen.findByText(/Painel da Lanchonete Sabor da Esquina/)
    expect(screen.queryByText(/Sobra no delivery/)).toBeNull()
    expect(screen.getAllByText('Sem receita').length).toBeGreaterThan(5)
    fireEvent.click(screen.getByRole('button', { name: 'Montar receita: X-Burger' }))

    // 4. Receita: texto pronto, leitura gravada, itens destacados
    expect(screen.getByLabelText(/O que vai neste prato/)).toHaveProperty('value', 'pão, hambúrguer de 150g, 2 fatias de queijo e a embalagem')
    fireEvent.click(screen.getByRole('button', { name: 'Organizar com a IA' }))
    await screen.findByText(/Você escreveu “hambúrguer” e liguei a “Blend bovino”/)
    expect(screen.getByText(/Medida caseira \(2 fatias\)/)).toBeTruthy()

    // Sem informar as fatias, não salva
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar receita' }))
    expect(screen.getByRole('alert').textContent).toMatch(/Corrija as linhas marcadas/)

    // O visitante digita 36 g de queijo (2 fatias de 18 g) e confere
    const queijo = screen.getByText(/Medida caseira \(2 fatias\)/).closest('.item-ficha') as HTMLElement
    fireEvent.change(within(queijo).getByLabelText(/Quantidade/), { target: { value: '36' } })
    fireEvent.click(screen.getByLabelText('Conferi os itens destacados'))
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar receita' }))

    // 5. Diagnóstico: conta linha por linha (valores do calculos.py: casos-calculos.json, decompor do X-Burger)
    await screen.findAllByText('= Sobra para você')
    const conta = screen.getAllByText('= Sobra para você')[0].closest('.conta-pedido') as HTMLElement
    expect(within(conta).getByText('R$ 24,90')).toBeTruthy()
    expect(within(conta).getByText('R$ 9,37')).toBeTruthy() // ingredientes
    expect(within(conta).getByText('R$ 6,47')).toBeTruthy() // taxa do app 26%
    expect(within(conta).getByText('R$ 7,57')).toBeTruthy() // sobra
    expect(screen.getAllByText('Saudável').length).toBeGreaterThan(0)

    // Simulador (em desenvolvimento): preço baixo vira crítico
    const simulador = screen.getByLabelText('E se eu cobrar (R$)')
    fireEvent.change(simulador, { target: { value: '15' } })
    expect(screen.getAllByText('Crítico').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Em desenvolvimento').length).toBeGreaterThan(0)

    // Volta ao painel: agora o X-Burger tem número; e o ingrediente mais caro derruba a sobra
    fireEvent.click(screen.getByRole('button', { name: '← Painel' }))
    await screen.findByText(/Sobra no delivery/)
    // blend 37 → 42/kg: 150 g = R$ 0,75 a mais (variacao_sobra do X-Burger em casos-calculos.json)
    const impacto = document.querySelector('.demo-impacto li')!.textContent!.replace(/\s+/g, ' ')
    expect(impacto).toContain('X-Burger')
    expect(impacto).toContain('sobra R$ 7,57 → R$ 6,82')
    expect(impacto).toContain('-R$ 0,75 por pedido')

    // Recomeçar
    fireEvent.click(screen.getByRole('button', { name: 'Recomeçar a demo' }))
    expect(screen.getByRole('button', { name: 'Ler cardápio' })).toBeTruthy()

    expect(fetchEspiao).not.toHaveBeenCalled()
  })
})
