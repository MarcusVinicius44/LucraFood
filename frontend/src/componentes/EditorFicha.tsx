import { useState } from 'react'
import type { Ingrediente, IngredienteNovo, MotivoRevisao, Unidade } from '../api'
import { novaChave, type LinhaFicha, type ProblemasFicha } from '../fichaLinhas'
import { Etiqueta } from './Etiqueta'
import { FormIngrediente } from './FormIngrediente'

const UNIDADE_CURTA: Record<Unidade, string> = { g: 'g', ml: 'ml', un: 'un' }

/** Motivos que só pedem um olhar (o item já está completo); os outros pedem que o dono preencha algo. */
const MOTIVOS_LEVES: MotivoRevisao[] = ['nome_diferente', 'medida_salva']

/** Por que o item foi marcado para conferência (ia/ficha.py devolve o código). */
function textoDoMotivo(motivo: MotivoRevisao, linha: LinhaFicha, ingrediente?: Ingrediente): string | null {
  const unidade = ingrediente?.unidade
  switch (motivo) {
    case 'sem_ingrediente':
      return linha.ingrediente ? null : 'Não achei no seu cadastro. Escolha um ingrediente ou cadastre um novo.'
    case 'sem_quantidade':
      return linha.estimativa ? null : 'O texto não diz quanto vai. Informe a quantidade.'
    case 'sem_unidade':
      return `O texto tem o número, mas não a unidade. Confira se é em ${unidade ?? 'g ou ml'}.`
    case 'unidade_informal':
      return `Medida caseira (${linha.escrito ?? 'sem peso exato'}): informe quanto dá em ${unidade ?? 'g ou ml'}.`
    case 'unidade_incompativel':
      return `A unidade escrita (${linha.escrito}) não combina com o cadastro (${unidade}). Informe em ${unidade}.`
    case 'ingrediente_repetido':
      return 'Este ingrediente aparece em mais de uma linha. Some as quantidades em uma só.'
    case 'nome_diferente':
      return ingrediente
        ? `Você escreveu “${linha.nomeLido}” e liguei a “${ingrediente.nome}”. Confira se é o mesmo produto.`
        : null
    case 'medida_salva':
      return linha.estimativa
        ? 'Usei a medida que você me ensinou antes. Se mudou, corrija aqui; para eu esquecer, vá em Ingredientes.'
        : null
  }
}

export function EditorFicha({
  linhas,
  setLinhas,
  cadastro,
  mostrarProblemas,
  problemas,
  onCadastrar,
}: {
  linhas: LinhaFicha[]
  setLinhas: (f: (atual: LinhaFicha[]) => LinhaFicha[]) => void
  cadastro: Ingrediente[]
  mostrarProblemas: boolean
  problemas: ProblemasFicha
  onCadastrar: (dados: IngredienteNovo) => Promise<Ingrediente>
}) {
  const [cadastrando, setCadastrando] = useState<number | null>(null)
  const porId = new Map(cadastro.map((i) => [i.id, i]))
  const alterar = (chave: number, campos: Partial<LinhaFicha>) =>
    setLinhas((a) => a.map((l) => (l.chave === chave ? { ...l, ...campos } : l)))

  return (
    <div className="pilha">
      {linhas.map((l) => {
        const ing = l.ingrediente ? porId.get(l.ingrediente) : undefined
        const prob = mostrarProblemas ? problemas.get(l.chave) : undefined
        const avisos = l.motivos.flatMap((m) => {
          const texto = textoDoMotivo(m, l, ing)
          return texto ? [{ texto, leve: MOTIVOS_LEVES.includes(m) }] : []
        })
        const marcada = l.motivos.some((m) => !MOTIVOS_LEVES.includes(m))
        const conferir = !marcada && l.motivos.length > 0
        return (
          <div key={l.chave} className={`item-ficha${marcada ? ' item-marcado' : conferir ? ' item-conferir' : ''}`}>
            {l.nomeLido && (
              <div className="pequeno suave">
                Escrito: <strong>{l.nomeLido}</strong>
                {l.escrito ? ` · ${l.escrito}` : ''}
              </div>
            )}
            <div className="item-ficha-campos">
              <div className={`campo${prob?.ingrediente ? ' campo-invalido' : ''}`}>
                <label htmlFor={`ing-${l.chave}`}>Ingrediente</label>
                <select
                  id={`ing-${l.chave}`}
                  value={l.ingrediente ?? ''}
                  onChange={(e) => {
                    if (e.target.value === 'novo') return setCadastrando(l.chave)
                    alterar(l.chave, { ingrediente: e.target.value ? Number(e.target.value) : null })
                  }}
                >
                  <option value="">— escolha —</option>
                  {cadastro.map((i) => (
                    <option key={i.id} value={i.id}>{i.nome} ({UNIDADE_CURTA[i.unidade]})</option>
                  ))}
                  <option value="novo">+ Cadastrar novo…</option>
                </select>
                {prob?.ingrediente && <span className="campo-erro">{prob.ingrediente}</span>}
              </div>
              <div className={`campo${prob?.quantidade ? ' campo-invalido' : ''}`}>
                <label htmlFor={`qtd-${l.chave}`}>Quantidade{ing ? ` (${ing.unidade === 'un' ? 'unidades' : ing.unidade})` : ''}</label>
                <input
                  id={`qtd-${l.chave}`}
                  inputMode="decimal"
                  value={l.quantidade}
                  onChange={(e) => alterar(l.chave, { quantidade: e.target.value, estimativa: undefined })}
                />
                {prob?.quantidade && <span className="campo-erro">{prob.quantidade}</span>}
              </div>
              <button
                type="button"
                className="botao botao-texto item-remover"
                aria-label={`Remover ${ing?.nome ?? l.nomeLido ?? 'item'}`}
                onClick={() => setLinhas((a) => a.filter((x) => x.chave !== l.chave))}
              >
                Remover
              </button>
            </div>
            {l.estimativa && (
              <div className="linha pequeno">
                <Etiqueta origem={l.estimativa}>estimativa</Etiqueta>
                <span className="suave">{l.estimativa}</span>
              </div>
            )}
            {avisos.map((a) => (
              <div key={a.texto} className={`pequeno ${a.leve ? 'aviso-linha-leve' : 'aviso-linha'}`}>{a.texto}</div>
            ))}
            {!l.ingrediente && l.nomeLido && cadastrando !== l.chave && (
              <button type="button" className="botao botao-secundario botao-pequeno" onClick={() => setCadastrando(l.chave)}>
                Cadastrar “{l.nomeLido}”
              </button>
            )}
            {cadastrando === l.chave && (
              <div className="cartao">
                <h3>Novo ingrediente</h3>
                <FormIngrediente
                  inicial={{ nome: l.nomeLido ?? '', unidade: l.unidadeLida ?? 'g' }}
                  textoBotao="Cadastrar e usar"
                  onCancelar={() => setCadastrando(null)}
                  onSalvar={async (dados) => {
                    const criado = await onCadastrar(dados)
                    // A quantidade lida só vale se a unidade cadastrada for a mesma do texto.
                    const manter = l.unidadeLida && l.unidadeLida === criado.unidade
                    alterar(l.chave, {
                      ingrediente: criado.id,
                      quantidade: manter ? l.quantidade : '',
                      motivos: l.motivos.filter((m) => m !== 'sem_ingrediente'),
                    })
                    setCadastrando(null)
                  }}
                />
              </div>
            )}
          </div>
        )
      })}
      <button
        type="button"
        className="botao botao-secundario"
        onClick={() => setLinhas((a) => [...a, { chave: novaChave(), ingrediente: null, quantidade: '', motivos: [] }])}
      >
        + Adicionar ingrediente
      </button>
    </div>
  )
}
