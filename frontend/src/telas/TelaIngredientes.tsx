import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import {
  ErroApi,
  apagarIngrediente,
  atualizarIngrediente,
  criarIngrediente,
  esquecerMedida,
  listarIngredientes,
  type Ingrediente,
  type MedidaCaseira,
} from '../api'
import { restauranteSalvo } from '../armazenamento'
import { Carregando } from '../componentes/Carregando'
import { FormIngrediente } from '../componentes/FormIngrediente'
import { formatarQuantidade, formatarReais, formatarReaisUnitario } from '../formato'

const POR_UNIDADE: Record<string, string> = { g: 'por grama', ml: 'por ml', un: 'por unidade' }

export function TelaIngredientes() {
  const salvo = restauranteSalvo()
  const [lista, setLista] = useState<Ingrediente[] | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [novo, setNovo] = useState(false)
  const [editando, setEditando] = useState<number | null>(null)
  const [aviso, setAviso] = useState<{ id: number; texto: string } | null>(null)
  const [busca, setBusca] = useState('')

  useEffect(() => {
    if (!salvo) return
    listarIngredientes(salvo.id)
      .then(setLista)
      .catch((e: Error) => setErro(e.message))
  }, [salvo?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!salvo) return <Navigate to="/app/foto" replace />
  if (erro) return <div className="aviso aviso-erro" role="alert">{erro}</div>
  if (!lista) return <Carregando titulo="Carregando ingredientes…" />

  const ordenar = (l: Ingrediente[]) => [...l].sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'))
  const filtrados = busca.trim()
    ? lista.filter((i) => i.nome.toLocaleLowerCase('pt-BR').includes(busca.trim().toLocaleLowerCase('pt-BR')))
    : lista

  async function esquecer(ingrediente: Ingrediente, medida: MedidaCaseira) {
    setAviso(null)
    try {
      await esquecerMedida(medida.id)
      setLista((l) =>
        (l ?? []).map((i) => (i.id === ingrediente.id ? { ...i, medidas: (i.medidas ?? []).filter((m) => m.id !== medida.id) } : i)),
      )
    } catch (e) {
      setAviso({ id: ingrediente.id, texto: e instanceof ErroApi ? e.message : 'Erro inesperado ao esquecer a medida.' })
    }
  }

  async function apagar(ingrediente: Ingrediente) {
    setAviso(null)
    try {
      await apagarIngrediente(ingrediente.id)
      setLista((l) => (l ?? []).filter((i) => i.id !== ingrediente.id))
    } catch (e) {
      const falha = e instanceof ErroApi ? e : new ErroApi(0, 'Erro inesperado ao apagar.')
      const pratos = Array.isArray(falha.dados.pratos) ? ` Usado em: ${(falha.dados.pratos as string[]).join(', ')}.` : ''
      setAviso({ id: ingrediente.id, texto: falha.message + pratos })
    }
  }

  return (
    <div className="pilha">
      <div>
        <h1>Ingredientes</h1>
        <p className="suave">
          Cadastre do jeito que você compra: o preço e quanto vem na embalagem. O sistema calcula o custo por grama, ml ou unidade.
        </p>
      </div>

      {novo ? (
        <div className="cartao">
          <h2>Novo ingrediente</h2>
          <FormIngrediente
            textoBotao="Cadastrar"
            onCancelar={() => setNovo(false)}
            onSalvar={async (dados) => {
              const criado = await criarIngrediente(salvo.id, dados)
              setLista((l) => ordenar([...(l ?? []), criado]))
              setNovo(false)
            }}
          />
        </div>
      ) : (
        <button className="botao botao-primario" onClick={() => setNovo(true)}>+ Cadastrar ingrediente</button>
      )}

      {lista.length > 6 && (
        <div className="campo">
          <label htmlFor="busca">Procurar</label>
          <input id="busca" value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Nome do ingrediente" />
        </div>
      )}

      {lista.length === 0 && !novo && (
        <p className="suave">Nenhum ingrediente cadastrado ainda. Você também pode cadastrar enquanto monta a ficha de um prato.</p>
      )}

      <div className="pilha">
        {filtrados.map((ing) =>
          editando === ing.id ? (
            <div key={ing.id} className="cartao">
              <FormIngrediente
                inicial={ing}
                textoBotao="Salvar"
                onCancelar={() => setEditando(null)}
                onSalvar={async (dados) => {
                  const atualizado = await atualizarIngrediente(ing.id, dados)
                  setLista((l) => ordenar((l ?? []).map((i) => (i.id === ing.id ? atualizado : i))))
                  setEditando(null)
                }}
              />
            </div>
          ) : (
            <article key={ing.id} className="cartao pilha-curta">
              <div className="linha" style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <strong>{ing.nome}</strong>
                  <div className="suave pequeno">
                    {formatarReais(ing.preco_embalagem)} a embalagem de {formatarQuantidade(ing.quantidade_embalagem, ing.unidade)}
                  </div>
                  <div className="pequeno">
                    {formatarReaisUnitario(ing.custo_por_unidade)} {POR_UNIDADE[ing.unidade]}
                  </div>
                  {(ing.medidas ?? []).map((m) => (
                    <div key={m.id} className="pequeno suave medida-caseira">
                      1 {m.medida} = {formatarQuantidade(m.quantidade, ing.unidade)}
                      <button
                        className="botao botao-texto botao-pequeno"
                        aria-label={`Esquecer 1 ${m.medida} de ${ing.nome}`}
                        title="Na próxima receita, o sistema volta a perguntar"
                        onClick={() => esquecer(ing, m)}
                      >
                        Esquecer
                      </button>
                    </div>
                  ))}
                </div>
                <div className="linha">
                  <button className="botao botao-texto" onClick={() => { setAviso(null); setEditando(ing.id) }}>Editar</button>
                  <button className="botao botao-texto" onClick={() => apagar(ing)}>Apagar</button>
                </div>
              </div>
              {aviso?.id === ing.id && <div className="aviso aviso-erro" role="alert">{aviso.texto}</div>}
            </article>
          ),
        )}
      </div>
    </div>
  )
}
