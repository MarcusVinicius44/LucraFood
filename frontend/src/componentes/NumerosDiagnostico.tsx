import type { Diagnostico } from '../api'
import { formatarPct, formatarReais } from '../formato'
import { ContaPedido } from './ContaPedido'
import { Etiqueta } from './Etiqueta'

/**
 * Números do diagnóstico, todos calculados no backend (calculos.py).
 * Prato pendente (sem preço, sem ficha, taxas impossíveis) mostra só a explicação, nenhum número:
 * custo zero daria um falso "saudável".
 */
export function NumerosDiagnostico({
  diagnostico,
  margemDesejada,
  mostrarConta = false,
  embalagemNaReceita = false,
}: {
  diagnostico: Diagnostico
  margemDesejada: string
  mostrarConta?: boolean // a conta linha por linha aparece na tela do prato, não em cada cartão do painel
  embalagemNaReceita?: boolean
}) {
  if (!diagnostico.semaforo) {
    return <p className="suave pequeno" style={{ margin: 0 }}>{diagnostico.mensagem}</p>
  }
  return (
    <>
      <div className="numeros">
        <div className="numero">
          <span className="numero-rotulo">Margem delivery</span>
          <span className="numero-valor">{formatarPct(diagnostico.margem_delivery_pct)}</span>
        </div>
        <div className="numero">
          <span className="numero-rotulo">Margem balcão</span>
          <span className="numero-valor">{formatarPct(diagnostico.margem_balcao_pct)}</span>
        </div>
        <div className="numero">
          <span className="numero-rotulo">Custo por porção</span>
          <span className="numero-valor">{formatarReais(diagnostico.custo)}</span>
        </div>
      </div>
      {mostrarConta && diagnostico.conta && <ContaPedido conta={diagnostico.conta} embalagemNaReceita={embalagemNaReceita} />}
      {diagnostico.preco_sugerido_delivery && (
        <div className="sugestao">
          <Etiqueta origem={`Custo da sua ficha + taxas do restaurante, para chegar a ${formatarPct(margemDesejada)} de margem no delivery.`}>
            sugestão
          </Etiqueta>
          <span>
            Preço no delivery: <strong>{formatarReais(diagnostico.preco_sugerido_delivery)}</strong>
          </span>
          <span className="suave pequeno">para chegar a {formatarPct(margemDesejada)} de margem</span>
        </div>
      )}
    </>
  )
}
