// Demo interativa da landing: o fluxo real (foto → revisão → painel → ficha → diagnóstico) com as
// respostas da IA gravadas e as contas do calculosDemo.ts. Fica isolada em src/demo/ e NUNCA chama /api.
import { useCallback, useState, type ReactNode } from 'react'
import { DemoFoto } from './DemoFoto'
import { DemoPainel } from './DemoPainel'
import { DemoPrato, type Modo } from './DemoPrato'
import { DemoRevisao } from './DemoRevisao'
import { PRATOS_LIDOS, type LinhaFicha, type PratoDemo } from './dadosDemo'
import './demo.css'

export type Etapa = 'foto' | 'revisao' | 'painel' | 'prato'

/** Prato na demo: `origem` = posição na leitura gravada (liga à receita gravada mesmo se o nome mudar). */
export interface PratoNaDemo extends PratoDemo {
  origem: number
}

/** O guia: o que fazer em cada passo. O próximo botão pulsa (data-guia). */
const GUIA = [
  'leia o cardápio com a IA',
  'confira os preços e confirme',
  'abra o X-Burger para montar a receita',
  'organize a receita e confirme',
  'veja quanto sobra no delivery',
]

type Aparelho = 'computador' | 'celular'

export default function Demo({ atrasoMs = 2000, fechamento }: { atrasoMs?: number; fechamento?: ReactNode }) {
  const [etapa, setEtapa] = useState<Etapa>('foto')
  const [pratos, setPratos] = useState<PratoNaDemo[]>([])
  const [fichas, setFichas] = useState<Record<number, LinhaFicha[]>>({})
  const [aberto, setAberto] = useState<number | null>(null)
  const [modoPrato, setModoPrato] = useState<Modo>('texto')
  const [aparelho, setAparelho] = useState<Aparelho>('computador')
  const aoMudarModo = useCallback((m: Modo) => setModoPrato(m), [])

  function recomecar() {
    setEtapa('foto')
    setPratos([])
    setFichas({})
    setAberto(null)
  }

  const prato = aberto === null ? null : pratos.find((p) => p.origem === aberto) ?? null
  const temFicha = Object.keys(fichas).length > 0
  const passo =
    etapa === 'foto' ? 1 : etapa === 'revisao' ? 2 : etapa === 'painel' ? (temFicha ? 5 : 3) : modoPrato === 'pronto' ? 5 : 4
  const concluido = passo === 5

  return (
    <div className="demo-palco">
      <div className="demo-controles">
        <div className="demo-aparelhos" role="group" aria-label="Ver a demo como">
          {(['computador', 'celular'] as Aparelho[]).map((a) => (
            <button key={a} type="button" aria-pressed={aparelho === a} onClick={() => setAparelho(a)}>
              {a === 'computador' ? 'Computador' : 'Celular'}
            </button>
          ))}
        </div>
        <div className="demo-guia" aria-live="polite">
          <span className="demo-guia-texto">
            <strong>Passo {passo} de 5:</strong> {concluido ? 'pronto! Essa é a conta do prato.' : GUIA[passo - 1]}
          </span>
          <span className="demo-progresso" aria-hidden="true">
            <span style={{ width: `${(concluido ? 5 : passo - 1) * 20}%` }} />
          </span>
        </div>
      </div>

      <div className={`demo demo-${aparelho}${concluido ? '' : ' demo-guiada'}`}>
        <div className="demo-barra">
          <span className="demo-pontos" aria-hidden="true"><span /><span /><span /></span>
          <span className="demo-selo">DEMO</span>
          <span className="demo-endereco">lanchonete de exemplo</span>
          {etapa !== 'foto' && (
            <button type="button" className="botao botao-texto demo-recomecar" onClick={recomecar}>
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
              onModo={aoMudarModo}
            />
          )}
        </div>
      </div>

      {concluido && fechamento && <div className="demo-fechamento">{fechamento}</div>}
    </div>
  )
}
