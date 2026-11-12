// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { CenaTopo } from './CenaTopo'
import { Cupom } from './Cupom'
import { Landing } from './Landing'
import { PorDentro } from './PorDentro'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('página de venda', () => {
  it('tem título acessível, CTA do piloto no WhatsApp, link para /por-dentro e nenhuma chamada de rede', () => {
    const fetchEspiao = vi.fn()
    vi.stubGlobal('fetch', fetchEspiao)
    render(<MemoryRouter><Landing /></MemoryRouter>)
    expect(screen.getByRole('heading', { level: 1, name: 'Quanto sobra de cada prato depois da taxa do app?' })).toBeTruthy()
    const ctas = screen.getAllByRole('link', { name: /piloto gratuito/i })
    expect(ctas.some((a) => a.getAttribute('href')!.startsWith('https://wa.me/'))).toBe(true)
    expect(screen.getByRole('link', { name: /Por dentro/ }).getAttribute('href')).toBe('/por-dentro')
    expect(screen.getByText(/Criado por/)).toBeTruthy()
    expect(screen.queryByText(/portfólio/i)).toBeNull()
    // o número de WhatsApp nunca aparece escrito
    expect(document.body.textContent).not.toMatch(/79\s?9?9975/)
    expect(fetchEspiao).not.toHaveBeenCalled()
  })

  it('números do problema mantêm o valor certo para leitor de tela', () => {
    render(<MemoryRouter><Landing /></MemoryRouter>)
    for (const v of ['1,6 milhão', '~380 mil', '71%', '16% a 25%', '43%']) expect(screen.getByText(v)).toBeTruthy()
  })

  it('cupom e cena usam a conta da demo (decompor do X-Burger, igual ao calculos.py)', () => {
    render(<><Cupom /><CenaTopo /></>)
    // casos-calculos.json: X-Burger R$ 24,90 → sobra R$ 7,57 (taxa 26%, imposto 6%)
    expect(screen.getAllByText('R$ 24,90').length).toBeGreaterThan(0)
    expect(screen.getAllByText('R$ 7,57').length).toBeGreaterThan(0)
    expect(screen.getByRole('img', { name: /No X-Burger de R\$ 24,90, sobram R\$ 7,57/ })).toBeTruthy()
  })

  it('/por-dentro mostra a parte técnica', () => {
    vi.stubGlobal('scrollTo', () => {})
    render(<MemoryRouter><PorDentro /></MemoryRouter>)
    expect(screen.getByRole('heading', { level: 1, name: 'Para quem quer ver a engenharia' })).toBeTruthy()
    expect(screen.getByText('251 de 254')).toBeTruthy()
  })
})
