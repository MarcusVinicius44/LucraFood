import { useLayoutEffect, useState, type CSSProperties, type RefObject } from 'react'
import { SemaforoSelo } from '../componentes/SemaforoSelo'
import { diagnosticoDemo, fichaExemplo, PRATOS_LIDOS, RESTAURANTE_DEMO } from '../demo/dadosDemo'
import foto from '../demo/fixtures/cardapio-sabor-da-esquina.png'
import { formatarPct, formatarReais } from '../formato'
import { semMovimento, useContador, useLinhaDoTempo, useVisivel } from './hooks'

// Cena do topo: o celular lê o cardápio, o painel monta os pratos e a sobra conta até o valor.
// Os números são os mesmos da demo (calculosDemo.ts, cópia testada do calculos.py), não imagem retocada.
const NOMES = ['X-Burger', 'X-Bacon', 'Batata Frita', 'X-Salada']

const LINHAS = NOMES.map((nome) => {
  const prato = PRATOS_LIDOS.find((p) => p.nome === nome)!
  const ficha = fichaExemplo(nome)
  const r = ficha && prato.preco ? diagnosticoDemo(prato.preco, ficha) : null
  return { prato, r }
})
const PRINCIPAL = LINHAS[0].r!
const BACON = LINHAS[1]
const ROTULO_SEMAFORO = { verde: 'Saudável', amarelo: 'Atenção', vermelho: 'Crítico' } as const

// Onde cada prato está na foto (px de 1440, medido no HTML do cardápio com o Chrome). A foto cobre a tela do
// celular pela altura, então a posição vertical em % vale direto. Só desenho: as caixas mostram a leitura acontecendo.
const LINHAS_NA_FOTO: [string, number][] = [
  ['X-Burger', 374], ['X-Salada', 448], ['X-Bacon', 522], ['X-Tudo', 596], ['Misto Quente', 670],
  ['Batata Frita', 812], ['Batata com Cheddar e Bacon', 859], ['Anéis de Cebola', 906],
  ['Refrigerante Lata', 1048], ['Suco Natural 500 ml', 1095], ['Água Mineral', 1142],
]
const caixa = (topo: number, i: number) =>
  ({ top: `${((topo - 7) / 1440) * 100}%`, height: `${(47 / 1440) * 100}%`, '--d': `${i * 70}ms` }) as CSSProperties

// Fases: 0 lendo · 1 caixas · 2–5 cada prato voa da foto para o painel · 6 sobra conta · 7 chips (segura e recomeça)
const FASES = 8
const PRIMEIRO_VOO = 2

/** Pílula que sai da linha do prato na foto e pousa na linha dele no painel (posições medidas na hora). */
function Voo({ cena, fase }: { cena: RefObject<HTMLDivElement | null>; fase: number }) {
  const [estilo, setEstilo] = useState<CSSProperties | null>(null)
  const i = fase - PRIMEIRO_VOO
  const linha = LINHAS[i]
  useLayoutEffect(() => {
    const raiz = cena.current
    if (!raiz || !linha || semMovimento()) {
      setEstilo(null)
      return
    }
    const de = raiz.querySelector(`[data-caixa="${linha.prato.nome}"]`)
    const para = raiz.querySelectorAll('.cena-lista li')[i]
    if (!de || !para) {
      setEstilo(null)
      return
    }
    const r = raiz.getBoundingClientRect()
    const a = de.getBoundingClientRect()
    const b = para.getBoundingClientRect()
    setEstilo({
      '--de-x': `${a.left - r.left}px`,
      '--de-y': `${a.top - r.top + a.height / 2}px`,
      '--para-x': `${b.left - r.left + 12}px`,
      '--para-y': `${b.top - r.top + b.height / 2}px`,
    } as CSSProperties)
  }, [cena, linha, i])
  if (!linha || !estilo) return null
  return (
    <span key={fase} className="cena-voo" style={estilo} aria-hidden="true">
      {linha.prato.nome} <strong>{formatarReais(linha.prato.preco)}</strong>
    </span>
  )
}

export function CenaTopo() {
  const [ref, visivel] = useVisivel<HTMLDivElement>('0px')
  const fase = useLinhaDoTempo(FASES, 950, 6000, visivel)
  const sobra = useContador(Number(PRINCIPAL.conta.sobra), fase >= 6, 1100)
  const voando = fase >= PRIMEIRO_VOO && fase < PRIMEIRO_VOO + LINHAS.length ? LINHAS[fase - PRIMEIRO_VOO].prato.nome : null
  const lidos = new Set(LINHAS.filter((_, i) => fase >= PRIMEIRO_VOO + i + 1).map((l) => l.prato.nome))

  return (
    <div ref={ref} className={`cena cena-fase-${fase}`} role="img" aria-label={`Exemplo do LucraFood: o celular lê o cardápio e o painel mostra quanto sobra de cada prato no delivery. No X-Burger de ${formatarReais(PRINCIPAL.conta.preco)}, sobram ${formatarReais(PRINCIPAL.conta.sobra)}.`}>
      <div className="cena-janela" aria-hidden="true">
        <div className="cena-janela-barra">
          <span /><span /><span />
          <strong>Painel · {RESTAURANTE_DEMO.nome}</strong>
        </div>
        <ul className="cena-lista">
          {LINHAS.map(({ prato, r }, i) => (
            <li key={prato.nome} className={fase >= PRIMEIRO_VOO + i ? 'entrou' : ''}>
              <div>
                <span className="cena-nome">{prato.nome}</span>
                <span className="cena-preco">{formatarReais(prato.preco)}</span>
              </div>
              {r ? (
                <div className="cena-dir">
                  <span className="cena-margem">{formatarPct(r.diagnostico.margem_delivery)}</span>
                  <SemaforoSelo semaforo={r.diagnostico.semaforo} />
                </div>
              ) : (
                <div className="cena-dir">
                  <SemaforoSelo semaforo={null} rotulo="Sem receita" />
                </div>
              )}
            </li>
          ))}
        </ul>
        <div className={`cena-sobra${fase >= 6 ? ' entrou' : ''}`}>
          <span>Sobra no X-Burger, por pedido no app</span>
          <strong>{formatarReais(sobra.toFixed(2))}</strong>
        </div>
      </div>

      <div className="cena-celular" aria-hidden="true">
        <div className="cena-celular-tela">
          <img src={foto} alt="" width={540} height={720} />
          <span className="cena-scan" />
          {LINHAS_NA_FOTO.map(([nome, topo], i) => (
            <span
              key={nome}
              data-caixa={nome}
              className={`cena-caixa${fase >= 1 ? ' entrou' : ''}${voando === nome ? ' alvo' : ''}${lidos.has(nome) ? ' lido' : ''}`}
              style={caixa(topo, i)}
            />
          ))}
          <span className="cena-celular-status">{fase <= 1 ? 'Lendo o cardápio…' : `${PRATOS_LIDOS.length} pratos lidos ✓`}</span>
        </div>
      </div>

      <span className={`cena-chip cena-chip-1${fase >= 7 ? ' entrou' : ''}`} aria-hidden="true">
        Taxa do app <strong>−{formatarReais(PRINCIPAL.conta.taxa_app)}</strong>
      </span>
      {BACON.r && (
        <span className={`cena-chip cena-chip-2 cena-chip-${BACON.r.diagnostico.semaforo}${fase >= 7 ? ' entrou' : ''}`} aria-hidden="true">
          {BACON.prato.nome}: <strong>{ROTULO_SEMAFORO[BACON.r.diagnostico.semaforo]}</strong>
        </span>
      )}
      <span className={`cena-chip cena-chip-3${fase >= 2 ? ' entrou' : ''}`} aria-hidden="true">
        Preço ilegível? Fica em branco
      </span>
      <Voo cena={ref} fase={fase} />
    </div>
  )
}
