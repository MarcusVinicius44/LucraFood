import { useState } from 'react'
import { lerPreco, precoParaCampo } from '../formato'
import type { PratoNaDemo } from './Demo'
import { GRAVACAO } from './dadosDemo'
import { SeloGravado } from './DemoFoto'

/** Revisão: o visitante corrige nome e preço, como no app (a IA lê, o dono confere). */
export function DemoRevisao({ pratos, onConfirmar }: { pratos: PratoNaDemo[]; onConfirmar: (p: PratoNaDemo[]) => void }) {
  const [campos, setCampos] = useState(pratos.map((p) => ({ nome: p.nome, preco: precoParaCampo(p.preco) })))
  const [tentou, setTentou] = useState(false)

  const lidos = campos.map((c) => ({ nome: c.nome.trim(), preco: lerPreco(c.preco) }))
  const invalidos = lidos.filter((l) => !l.nome || !l.preco.ok).length

  function confirmar() {
    setTentou(true)
    if (invalidos) return
    onConfirmar(
      pratos.map((p, i) => ({ ...p, nome: lidos[i].nome, preco: (lidos[i].preco as { ok: true; valor: string | null }).valor })),
    )
  }

  return (
    <div className="pilha">
      <div>
        <h3>Confira os pratos que a IA leu</h3>
        <p className="suave pequeno" style={{ margin: 0 }}>
          {pratos.length} pratos em {String(GRAVACAO.segundos).replace('.', ',')} s. Corrija o que quiser: nada é salvo antes de você
          confirmar.
        </p>
        <SeloGravado />
      </div>
      <ul className="demo-revisao">
        {pratos.map((p, i) => {
          const erroPreco = tentou && !lidos[i].preco.ok ? (lidos[i].preco as { ok: false; erro: string }).erro : null
          const erroNome = tentou && !lidos[i].nome ? 'Informe o nome' : null
          return (
            <li key={p.origem} className="prato-revisao">
              <div className="prato-revisao-campos">
                <div className={`campo${erroNome ? ' campo-invalido' : ''}`}>
                  <label htmlFor={`demo-nome-${i}`}>Prato{p.categoria ? ` · ${p.categoria.toLowerCase()}` : ''}</label>
                  <input
                    id={`demo-nome-${i}`}
                    value={campos[i].nome}
                    onChange={(e) => setCampos((c) => c.map((x, j) => (j === i ? { ...x, nome: e.target.value } : x)))}
                  />
                  {erroNome && <span className="campo-erro">{erroNome}</span>}
                </div>
                <div className={`campo${erroPreco ? ' campo-invalido' : ''}`}>
                  <label htmlFor={`demo-preco-${i}`}>Preço (R$)</label>
                  <input
                    id={`demo-preco-${i}`}
                    inputMode="decimal"
                    value={campos[i].preco}
                    onChange={(e) => setCampos((c) => c.map((x, j) => (j === i ? { ...x, preco: e.target.value } : x)))}
                  />
                  {erroPreco && <span className="campo-erro">{erroPreco}</span>}
                </div>
              </div>
            </li>
          )
        })}
      </ul>
      {tentou && invalidos > 0 && (
        <div className="aviso aviso-erro" role="alert">Corrija os campos marcados.</div>
      )}
      <button type="button" className="botao botao-primario" onClick={confirmar}>
        Confirmar e ver o painel
      </button>
    </div>
  )
}
