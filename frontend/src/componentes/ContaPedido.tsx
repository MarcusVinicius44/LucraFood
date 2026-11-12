import { formatarReais } from '../formato'

/** A conta de um pedido no delivery, em reais. Os valores chegam prontos (calculos.decompor). */
export interface ContaPedidoValores {
  preco: string
  ingredientes: string
  embalagem: string
  impostos: string
  taxa_app: string
  sobra: string
}

export function ContaPedido({
  conta,
  titulo = 'Num pedido pelo app de delivery',
  embalagemNaReceita = false,
}: {
  conta: ContaPedidoValores
  titulo?: string
  embalagemNaReceita?: boolean // a embalagem foi cadastrada como item da receita (soma junto dos ingredientes)
}) {
  const negativa = Number(conta.sobra) < 0
  const linhas: [string, string][] = [
    ...(embalagemNaReceita
      ? ([['Ingredientes e embalagem', conta.ingredientes]] as [string, string][])
      : ([
          ['Ingredientes', conta.ingredientes],
          ['Embalagem', conta.embalagem],
        ] as [string, string][])),
    ['Impostos', conta.impostos],
    ['Taxa do app', conta.taxa_app],
  ]
  return (
    <div className="conta-pedido">
      <p className="conta-titulo">{titulo}</p>
      <dl>
        <div>
          <dt>Preço</dt>
          <dd>{formatarReais(conta.preco)}</dd>
        </div>
        {linhas.map(([rotulo, valor]) => (
          <div key={rotulo}>
            <dt>− {rotulo}</dt>
            <dd>{formatarReais(valor)}</dd>
          </div>
        ))}
        <div className={`conta-sobra ${negativa ? 'conta-sobra-negativa' : ''}`}>
          <dt>{negativa ? '= Prejuízo por pedido' : '= Sobra para você'}</dt>
          <dd>{formatarReais(conta.sobra)}</dd>
        </div>
      </dl>
    </div>
  )
}
