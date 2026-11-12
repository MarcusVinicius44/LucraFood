// Demo interativa da landing: o fluxo real (foto → revisão → painel → ficha → diagnóstico) com as
// respostas da IA gravadas e as contas do calculosDemo.ts. Fica isolada em src/demo/ e NUNCA chama /api.
import { useState } from 'react'
import { DemoFoto } from './DemoFoto'
import { DemoPainel } from './DemoPainel'
import { DemoPrato } from './DemoPrato'
import { DemoRevisao } from './DemoRevisao'
import { PRATOS_LIDOS, type LinhaFicha, type PratoDemo } from './dadosDemo'
import './demo.css'

export type Etapa = 'foto' | 'revisao' | 'painel' | 'prato'

/** Prato na demo: `origem` = posição na leitura gravada (liga à receita gravada mesmo se o nome mudar). */
export interface PratoNaDemo extends PratoDemo {
  origem: number
}

const ROTULOS: Record<Etapa, string> = { foto: '1. Foto', revisao: '2. Conferir', painel: '3. Painel', prato: '4. Receita' }

export default function Demo({ atrasoMs = 2000 }: { atrasoMs?: number }) {
  const [etapa, setEtapa] = useState<Etapa>('foto')
  const [pratos, setPratos] = useState<PratoNaDemo[]>([])
  const [fichas, setFichas] = useState<Record<number, LinhaFicha[]>>({})
  const [aberto, setAberto] = useState<number | null>(null)

  function recomecar() {
    setEtapa('foto')
    setPratos([])
    setFichas({})
    setAberto(null)
  }

  const prato = aberto === null ? null : pratos.find((p) => p.origem === aberto) ?? null

  return (
    <div className="demo">
      <div className="demo-barra">
        <span className="demo-selo">DEMO</span>
        <ol className="demo-etapas" aria-label="Etapas da demo">
          {(Object.keys(ROTULOS) as Etapa[]).map((e) => (
            <li key={e} aria-current={e === etapa ? 'step' : undefined}>
              {ROTULOS[e]}
            </li>
          ))}
        </ol>
        {etapa !== 'foto' && (
          <button type="button" className="botao botao-texto" onClick={recomecar}>
            Recomeçar a demo
          </button>
        )}
      </div>

      <div className="demo-tela" aria-live="polite">
        {etapa === 'foto' && (
          <DemoFoto
            atrasoMs={atrasoMs}
            onLido={() => {
              setPratos(PRATOS_LIDOS.map((p, i) => ({ ...p, origem: i })))
              setEtapa('revisao')
            }}
          />
        )}
        {etapa === 'revisao' && (
          <DemoRevisao
            pratos={pratos}
            onConfirmar={(conferidos) => {
              setPratos(conferidos)
              setEtapa('painel')
            }}
          />
        )}
        {etapa === 'painel' && (
          <DemoPainel
            pratos={pratos}
            fichas={fichas}
            onAbrir={(origem) => {
              setAberto(origem)
              setEtapa('prato')
            }}
          />
        )}
        {etapa === 'prato' && prato && (
          <DemoPrato
            key={prato.origem}
            prato={prato}
            fichaSalva={fichas[prato.origem] ?? null}
            atrasoMs={atrasoMs}
            onSalvar={(linhas) => setFichas((f) => ({ ...f, [prato.origem]: linhas }))}
            onVoltar={() => setEtapa('painel')}
          />
        )}
      </div>
    </div>
  )
}
