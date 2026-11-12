import { useState } from 'react'
import { Etiqueta } from '../componentes/Etiqueta'
import { SemaforoSelo } from '../componentes/SemaforoSelo'
import { formatarPct, formatarReais, lerPreco, precoParaCampo } from '../formato'
import { variacaoSobra } from './calculosDemo'
import type { PratoNaDemo } from './Demo'
import { diagnosticoDemo, FICHAS_GRAVADAS, INGREDIENTES_DEMO, itensCusto, PRATOS_LIDOS, RESTAURANTE_DEMO, type LinhaFicha } from './dadosDemo'

const temGravacao = (p: PratoNaDemo) => FICHAS_GRAVADAS.some((f) => f.prato === PRATOS_LIDOS[p.origem].nome)

export function DemoPainel({
  pratos,
  fichas,
  onAbrir,
}: {
  pratos: PratoNaDemo[]
  fichas: Record<number, LinhaFicha[]>
  onAbrir: (origem: number) => void
}) {
  const linhas = pratos.map((p) => {
    const ficha = fichas[p.origem]
    const r = ficha && p.preco ? diagnosticoDemo(p.preco, ficha) : null
    return { p, r, ficha }
  })
  const conta = (s: string) => linhas.filter((l) => l.r?.diagnostico.semaforo === s).length
  const semReceita = linhas.filter((l) => !l.r).length

  return (
    <div className="pilha">
      <div>
        <h3>Painel da {RESTAURANTE_DEMO.nome}</h3>
        <p className="suave pequeno" style={{ margin: 0 }}>
          Taxa do app {RESTAURANTE_DEMO.taxa_delivery_pct}%, impostos {RESTAURANTE_DEMO.impostos_pct}%, margem desejada{' '}
          {RESTAURANTE_DEMO.margem_desejada_pct}% (dados de exemplo).
        </p>
      </div>
      <div className="demo-resumo">
        <span><SemaforoSelo semaforo="verde" /> {conta('verde')}</span>
        <span><SemaforoSelo semaforo="amarelo" /> {conta('amarelo')}</span>
        <span><SemaforoSelo semaforo="vermelho" /> {conta('vermelho')}</span>
        <span><SemaforoSelo semaforo={null} rotulo="Sem receita" /> {semReceita}</span>
      </div>
      {semReceita === pratos.length && (
        <div className="aviso aviso-info">
          Ainda não dá para dizer quanto sobra: sem receita, o custo seria zero e todo prato pareceria lucrativo. Comece pelo{' '}
          <strong>X-Burger</strong>.
        </div>
      )}
      <ul className="demo-pratos">
        {linhas.map(({ p, r }) => (
          <li key={p.origem} className="cartao prato-painel">
            <div className="prato-painel-topo">
              <div>
                <span className="prato-painel-nome">{p.nome}</span>
                <div className="suave pequeno">{p.preco ? formatarReais(p.preco) : 'sem preço'}</div>
              </div>
              {r ? <SemaforoSelo semaforo={r.diagnostico.semaforo} /> : <SemaforoSelo semaforo={null} rotulo={p.preco ? 'Sem receita' : 'Sem preço'} />}
            </div>
            {r ? (
              <p className="pequeno" style={{ margin: 0 }}>
                Sobra no delivery <strong>{formatarReais(r.conta.sobra)}</strong> · margem {formatarPct(r.diagnostico.margem_delivery)}
              </p>
            ) : null}
            {temGravacao(p) ? (
              <button
                type="button"
                className="botao botao-secundario botao-pequeno"
                data-guia={!r && p.origem === 0 && Object.keys(fichas).length === 0 ? '' : undefined}
                onClick={() => onAbrir(p.origem)}
              >
                {r ? `Ver a conta: ${p.nome}` : `Montar receita: ${p.nome}`}
              </button>
            ) : (
              !r && <span className="suave pequeno">Nesta demo, só X-Burger, X-Bacon e Batata Frita têm receita gravada.</span>
            )}
          </li>
        ))}
      </ul>
      <IngredienteMaisCaro pratos={pratos} fichas={fichas} />
    </div>
  )
}

/** Em desenvolvimento: o que acontece com a sobra de cada prato se um ingrediente subir de preço. */
function IngredienteMaisCaro({ pratos, fichas }: { pratos: PratoNaDemo[]; fichas: Record<number, LinhaFicha[]> }) {
  const [id, setId] = useState(2) // Blend bovino
  const ing = INGREDIENTES_DEMO.find((i) => i.id === id)!
  const [novo, setNovo] = useState('42,00')
  const lido = lerPreco(novo)
  const afetados = pratos.filter((p) => p.preco && fichas[p.origem]?.some((l) => l.ingrediente === id))
  const r = RESTAURANTE_DEMO

  return (
    <section className="cartao pilha demo-em-dev" aria-labelledby="demo-mais-caro">
      <div className="linha">
        <Etiqueta origem="Funciona na demo; no app real depende do histórico de preço, ainda em desenvolvimento.">Em desenvolvimento</Etiqueta>
      </div>
      <h4 id="demo-mais-caro">E se um ingrediente ficar mais caro?</h4>
      <div className="grade-2">
        <div className="campo">
          <label htmlFor="demo-ing">Ingrediente</label>
          <select
            id="demo-ing"
            value={id}
            onChange={(e) => {
              const n = Number(e.target.value)
              setId(n)
              setNovo(precoParaCampo(INGREDIENTES_DEMO.find((i) => i.id === n)!.preco_embalagem))
            }}
          >
            {INGREDIENTES_DEMO.map((i) => (
              <option key={i.id} value={i.id}>{i.nome}</option>
            ))}
          </select>
        </div>
        <div className={`campo${lido.ok ? '' : ' campo-invalido'}`}>
          <label htmlFor="demo-ing-preco">
            Preço novo por {ing.quantidade_embalagem} {ing.unidade} (era {formatarReais(ing.preco_embalagem)})
          </label>
          <input id="demo-ing-preco" inputMode="decimal" value={novo} onChange={(e) => setNovo(e.target.value)} />
          {!lido.ok && <span className="campo-erro">{lido.erro}</span>}
        </div>
      </div>
      {afetados.length === 0 ? (
        <p className="suave pequeno" style={{ margin: 0 }}>
          Nenhuma receita montada usa {ing.nome} ainda. Monte a receita do X-Burger ou do X-Bacon e volte aqui.
        </p>
      ) : (
        lido.ok &&
        lido.valor && (
          <ul className="demo-impacto">
            {afetados.map((p) => {
              const ficha = fichas[p.origem]
              const v = variacaoSobra(p.preco!, itensCusto(ficha), itensCusto(ficha, { [id]: lido.valor! }), 0, 1, r.taxa_delivery_pct, r.impostos_pct)
              const antes = diagnosticoDemo(p.preco!, ficha).diagnostico.semaforo
              const depois = diagnosticoDemo(p.preco!, ficha, { [id]: lido.valor! }).diagnostico.semaforo
              const caiu = Number(v.diferenca) < 0
              return (
                <li key={p.origem}>
                  <strong>{p.nome}</strong>
                  <span>
                    sobra {formatarReais(v.antes)} → <strong>{formatarReais(v.depois)}</strong>{' '}
                    <span className={caiu ? 'demo-queda' : 'suave'}>({caiu ? '' : '+'}{formatarReais(v.diferenca)} por pedido)</span>
                  </span>
                  <span className="linha">
                    <SemaforoSelo semaforo={antes} /> → <SemaforoSelo semaforo={depois} />
                  </span>
                </li>
              )
            })}
          </ul>
        )
      )}
    </section>
  )
}
