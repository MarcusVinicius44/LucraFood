import { useState } from 'react'
import { SemaforoSelo } from '../componentes/SemaforoSelo'
import { diagnosticoDemo, fichaExemplo, PRATOS_LIDOS, RESTAURANTE_DEMO } from '../demo/dadosDemo'
import { formatarPct, formatarReais } from '../formato'
import { useLinhaDoTempo, useValorSuave, useVisivel } from './hooks'

// "A conta que ninguém te mostra": o pedido do X-Burger da demo, descontado linha por linha.
// Valores de decompor() do calculosDemo.ts (os mesmos de calculos.py, conferidos em casos-calculos.json).
const PRATO = PRATOS_LIDOS.find((p) => p.nome === 'X-Burger')!
const R = diagnosticoDemo(PRATO.preco!, fichaExemplo('X-Burger')!)
const C = R.conta
const P = Number(C.preco)

const DESCONTOS = [
  { chave: 'ingredientes', rotulo: 'Ingredientes e embalagem', valor: C.ingredientes },
  { chave: 'impostos', rotulo: `Imposto (${RESTAURANTE_DEMO.impostos_pct}%)`, valor: C.impostos },
  { chave: 'taxa', rotulo: `Taxa do app (${RESTAURANTE_DEMO.taxa_delivery_pct}%)`, valor: C.taxa_app },
]

/** Quanto ainda sobra depois de cada linha (só exibição, a partir dos valores já calculados). */
const RESTANTE = [P, P - Number(C.ingredientes), P - Number(C.ingredientes) - Number(C.impostos), Number(C.sobra)]

export function Cupom() {
  const [rodada, setRodada] = useState(0)
  const [ref, visivel] = useVisivel<HTMLDivElement>()
  return (
    <div ref={ref}>
      <CupomAnimado key={rodada} ativo={visivel} onRepetir={() => setRodada((r) => r + 1)} />
    </div>
  )
}

function CupomAnimado({ ativo, onRepetir }: { ativo: boolean; onRepetir: () => void }) {
  // 0 preço · 1 ingredientes · 2 imposto · 3 taxa · 4 sobra
  const fase = useLinhaDoTempo(5, 1100, 0, ativo, false)
  const exibido = useValorSuave(RESTANTE[Math.min(fase, 3)], 700)

  return (
    <div className={`cupom cupom-fase-${fase}`}>
      <div className="cupom-papel">
        <p className="cupom-cabeca">
          <strong>{RESTAURANTE_DEMO.nome}</strong>
          <span>Pedido pelo app de delivery · exemplo</span>
        </p>
        <ul className="cupom-linhas">
          <li className="cupom-linha entrou">
            <span>1× {PRATO.nome}</span>
            <strong>{formatarReais(C.preco)}</strong>
          </li>
          {DESCONTOS.map((d, i) => (
            <li key={d.chave} className={`cupom-linha cupom-desconto${fase >= i + 1 ? ' entrou' : ''}`}>
              <span>− {d.rotulo}</span>
              <strong>−{formatarReais(d.valor)}</strong>
            </li>
          ))}
          <li className={`cupom-linha cupom-total${fase >= 4 ? ' entrou' : ''}`}>
            <span>= Sobra para você</span>
            <strong>{formatarReais(C.sobra)}</strong>
          </li>
        </ul>
        <div className="cupom-barra" aria-hidden="true">
          {DESCONTOS.map((d, i) => (
            <span
              key={d.chave}
              className={`cupom-seg cupom-seg-${d.chave}${fase >= i + 1 ? ' saiu' : ''}`}
              style={{ flexBasis: `${(Number(d.valor) / P) * 100}%` }}
            />
          ))}
          <span className="cupom-seg cupom-seg-sobra" style={{ flexBasis: `${(Number(C.sobra) / P) * 100}%` }} />
        </div>
        <p className="cupom-restante" aria-hidden="true">
          Ainda é seu: <strong>{formatarReais(exibido.toFixed(2))}</strong>
        </p>
      </div>
      <div className={`cupom-conclusao${fase >= 4 ? ' entrou' : ''}`}>
        <p>
          De cada {formatarReais(C.preco)} que o cliente paga, ficam <strong>{formatarReais(C.sobra)}</strong> para você
          ({formatarPct(R.diagnostico.margem_delivery)}).
        </p>
        <p className="linha">
          <SemaforoSelo semaforo={R.diagnostico.semaforo} />
          <span className="suave pequeno">
            Saudável a partir de {RESTAURANTE_DEMO.margem_desejada_pct}%, crítico abaixo de {RESTAURANTE_DEMO.margem_minima_pct}%.
            Os limites são seus.
          </span>
        </p>
        <button type="button" className="botao botao-texto" onClick={onRepetir}>
          Ver a conta de novo
        </button>
      </div>
    </div>
  )
}
