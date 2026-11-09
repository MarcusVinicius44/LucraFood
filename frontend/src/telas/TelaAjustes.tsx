import { useEffect, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { ErroApi, atualizarRestaurante, buscarRestaurante, type Restaurante } from '../api'
import { restauranteSalvo } from '../armazenamento'
import { Carregando } from '../componentes/Carregando'
import { lerPercentual, numeroParaCampo } from '../formato'

type Campo = 'taxa_delivery_pct' | 'impostos_pct' | 'margem_desejada_pct' | 'margem_minima_pct'

const CAMPOS: { campo: Campo; rotulo: string; ajuda: string }[] = [
  { campo: 'taxa_delivery_pct', rotulo: 'Taxa do app de delivery (%)', ajuda: 'Comissão que o app cobra sobre cada pedido. Ex.: 23' },
  { campo: 'impostos_pct', rotulo: 'Impostos (%)', ajuda: 'Ex.: Simples Nacional, 6' },
  { campo: 'margem_desejada_pct', rotulo: 'Margem que você quer (%)', ajuda: 'Acima dela o prato fica Saudável. Padrão: 30' },
  { campo: 'margem_minima_pct', rotulo: 'Margem mínima (%)', ajuda: 'Abaixo dela o prato fica Crítico; entre as duas, Atenção. Padrão: 10' },
]

export function TelaAjustes() {
  const salvo = restauranteSalvo()
  const [restaurante, setRestaurante] = useState<Restaurante | null>(null)
  const [valores, setValores] = useState<Record<Campo, string> | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)
  const [ok, setOk] = useState(false)

  useEffect(() => {
    if (!salvo) return
    buscarRestaurante(salvo.id)
      .then((r) => {
        setRestaurante(r)
        setValores(Object.fromEntries(CAMPOS.map(({ campo }) => [campo, numeroParaCampo(r[campo])])) as Record<Campo, string>)
      })
      .catch((e: Error) => setErro(e.message))
  }, [salvo?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!salvo) return <Navigate to="/foto" replace />
  if (!restaurante || !valores) return erro ? <div className="aviso aviso-erro">{erro}</div> : <Carregando titulo="Carregando…" />

  const lidos = Object.fromEntries(CAMPOS.map(({ campo }) => [campo, lerPercentual(valores[campo])])) as Record<Campo, ReturnType<typeof lerPercentual>>
  const erroDo = (campo: Campo) => {
    const l = lidos[campo]
    return !l.ok ? l.erro : l.valor === null ? 'Informe um valor (pode ser 0)' : null
  }
  const temErro = CAMPOS.some(({ campo }) => erroDo(campo))

  async function salvar(e: React.FormEvent) {
    e.preventDefault()
    if (enviando || temErro) return
    setEnviando(true)
    setErro(null)
    setOk(false)
    try {
      const campos = Object.fromEntries(CAMPOS.map(({ campo }) => [campo, (lidos[campo] as { valor: string }).valor]))
      setRestaurante(await atualizarRestaurante(salvo!.id, campos))
      setOk(true)
    } catch (e) {
      // 400 se a mínima passar da desejada (mesma mensagem do backend).
      setErro(e instanceof ErroApi ? e.message : 'Erro inesperado ao salvar.')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <form className="pilha" onSubmit={salvar} noValidate>
      <div>
        <h1>Taxas e margens</h1>
        <p className="suave">
          {restaurante.nome}. Esses números entram na conta de todos os pratos: o sistema desconta a taxa do app e os impostos do preço de
          venda para chegar à margem do delivery.
        </p>
      </div>
      <div className="cartao pilha">
        {CAMPOS.map(({ campo, rotulo, ajuda }) => (
          <div key={campo} className={`campo${erroDo(campo) ? ' campo-invalido' : ''}`}>
            <label htmlFor={campo}>{rotulo}</label>
            <input
              id={campo}
              inputMode="decimal"
              value={valores[campo]}
              onChange={(e) => {
                setValores({ ...valores, [campo]: e.target.value })
                setOk(false)
              }}
            />
            {erroDo(campo) ? <span className="campo-erro">{erroDo(campo)}</span> : <span className="suave pequeno">{ajuda}</span>}
          </div>
        ))}
      </div>
      {erro && <div className="aviso aviso-erro" role="alert">{erro}</div>}
      {ok && (
        <div className="aviso aviso-sucesso" role="status">
          Salvo. <Link to="/painel">Ver o painel atualizado</Link>
        </div>
      )}
      <button className="botao botao-primario" type="submit" disabled={enviando || temErro}>
        {enviando ? 'Salvando…' : 'Salvar'}
      </button>
    </form>
  )
}
