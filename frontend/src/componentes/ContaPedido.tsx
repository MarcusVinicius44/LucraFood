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

export function ContaPedido({ conta, titulo = 'Num pedido pelo app de delivery' }: { conta: ContaPedidoValores; titulo?: string }) {
  const negativa = Number(conta.sobra) < 0
  const linhas: [string, string][] = [
    ['Ingredientes', conta.ingredientes],
    ['Embalagem', conta.embalagem],
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
