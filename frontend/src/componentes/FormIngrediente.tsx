import { useId, useState } from 'react'
import { ErroApi, type IngredienteNovo, type Unidade } from '../api'
import { lerPreco, lerQuantidade, numeroParaCampo, precoParaCampo } from '../formato'

const UNIDADES: { valor: Unidade; rotulo: string; exemplo: string }[] = [
  { valor: 'g', rotulo: 'gramas (g)', exemplo: 'pacote de 1 kg = 1000' },
  { valor: 'ml', rotulo: 'mililitros (ml)', exemplo: 'garrafa de 1 litro = 1000' },
  { valor: 'un', rotulo: 'unidades', exemplo: 'pacote com 8 pães = 8' },
]

/**
 * Cadastro de ingrediente do jeito que o dono compra: preço e tamanho da embalagem.
 * O custo por grama/ml/unidade é calculado no backend, não aqui.
 */
export function FormIngrediente({
  inicial,
  textoBotao,
  onSalvar,
  onCancelar,
  unidadeTravada,
}: {
  inicial?: Partial<IngredienteNovo>
  textoBotao: string
  onSalvar: (dados: IngredienteNovo) => Promise<void>
  onCancelar?: () => void
  unidadeTravada?: string // motivo, quando a unidade não pode mudar (ingrediente já usado em ficha)
}) {
  const id = useId()
  const [nome, setNome] = useState(inicial?.nome ?? '')
  const [unidade, setUnidade] = useState<Unidade>(inicial?.unidade ?? 'g')
  const [preco, setPreco] = useState(precoParaCampo(inicial?.preco_embalagem ?? null))
  const [quantidade, setQuantidade] = useState(numeroParaCampo(inicial?.quantidade_embalagem))
  const [enviando, setEnviando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const [tentou, setTentou] = useState(false)

  const precoLido = lerPreco(preco)
  const qtdLida = lerQuantidade(quantidade)
  const erros = {
    nome: nome.trim() ? null : 'Dê um nome',
    preco: !precoLido.ok ? precoLido.erro : precoLido.valor === null ? 'Informe o preço da embalagem' : null,
    quantidade: !qtdLida.ok ? qtdLida.erro : qtdLida.valor === null ? 'Informe quanto vem na embalagem' : null,
  }
  const exemplo = UNIDADES.find((u) => u.valor === unidade)!.exemplo

  async function salvar(evento: React.FormEvent) {
    evento.preventDefault()
    setTentou(true)
    if (enviando || erros.nome || erros.preco || erros.quantidade) return
    setEnviando(true)
    setErro(null)
    try {
      await onSalvar({
        nome: nome.trim(),
        unidade,
        preco_embalagem: (precoLido as { valor: string }).valor,
        quantidade_embalagem: (qtdLida as { valor: string }).valor,
      })
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : 'Erro inesperado ao salvar o ingrediente.')
    } finally {
      setEnviando(false)
    }
  }

  const mostrar = (campo: keyof typeof erros) => (tentou ? erros[campo] : null)

  return (
    <form className="pilha" onSubmit={salvar} noValidate>
      <div className={`campo${mostrar('nome') ? ' campo-invalido' : ''}`}>
        <label htmlFor={`${id}-nome`}>Ingrediente</label>
        <input id={`${id}-nome`} value={nome} onChange={(e) => setNome(e.target.value)} placeholder="Ex.: Queijo muçarela" />
        {mostrar('nome') && <span className="campo-erro">{mostrar('nome')}</span>}
      </div>
      <div className="campo">
        <label htmlFor={`${id}-unidade`}>Medido em</label>
        <select
          id={`${id}-unidade`}
          value={unidade}
          disabled={!!unidadeTravada}
          onChange={(e) => setUnidade(e.target.value as Unidade)}
        >
          {UNIDADES.map((u) => (
            <option key={u.valor} value={u.valor}>{u.rotulo}</option>
          ))}
        </select>
        {unidadeTravada && <span className="suave pequeno">{unidadeTravada}</span>}
      </div>
      <div className="grade-2">
        <div className={`campo${mostrar('preco') ? ' campo-invalido' : ''}`}>
          <label htmlFor={`${id}-preco`}>Preço da embalagem (R$)</label>
          <input id={`${id}-preco`} inputMode="decimal" value={preco} onChange={(e) => setPreco(e.target.value)} placeholder="42,00" />
          {mostrar('preco') && <span className="campo-erro">{mostrar('preco')}</span>}
        </div>
        <div className={`campo${mostrar('quantidade') ? ' campo-invalido' : ''}`}>
          <label htmlFor={`${id}-qtd`}>Quanto vem ({unidade === 'un' ? 'unidades' : unidade})</label>
          <input id={`${id}-qtd`} inputMode="decimal" value={quantidade} onChange={(e) => setQuantidade(e.target.value)} placeholder="1000" />
          {mostrar('quantidade') ? (
            <span className="campo-erro">{mostrar('quantidade')}</span>
          ) : (
            <span className="suave pequeno">Ex.: {exemplo}</span>
          )}
        </div>
      </div>
      {erro && <div className="aviso aviso-erro" role="alert">{erro}</div>}
      <div className="linha">
        <button className="botao botao-primario" type="submit" disabled={enviando}>
          {enviando ? 'Salvando…' : textoBotao}
        </button>
        {onCancelar && (
          <button className="botao botao-texto" type="button" onClick={onCancelar}>
            Cancelar
          </button>
        )}
      </div>
    </form>
  )
}
