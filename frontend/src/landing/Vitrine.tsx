import { SemaforoSelo } from '../componentes/SemaforoSelo'
import { diagnosticoDemo, fichaExemplo, PRATOS_LIDOS, RESTAURANTE_DEMO } from '../demo/dadosDemo'
import { formatarPct, formatarReais } from '../formato'

/** Painel de exemplo no topo da landing: os mesmos dados e contas da demo, não uma imagem retocada. */
export function Vitrine() {
  const nomes = ['X-Burger', 'X-Bacon', 'Batata Frita', 'X-Salada']
  const linhas = nomes.map((nome) => {
    const prato = PRATOS_LIDOS.find((p) => p.nome === nome)!
    const ficha = fichaExemplo(nome)
    const r = ficha && prato.preco ? diagnosticoDemo(prato.preco, ficha) : null
    return { prato, r }
  })
  return (
    <figure className="lp-vitrine" aria-label="Exemplo do painel do LucraFood">
      <div className="lp-vitrine-tela">
        <div className="lp-vitrine-topo">
          <strong>{RESTAURANTE_DEMO.nome}</strong>
          <span className="suave pequeno">Taxa do app {RESTAURANTE_DEMO.taxa_delivery_pct}%</span>
        </div>
        <ul className="lp-vitrine-lista">
          {linhas.map(({ prato, r }) => (
            <li key={prato.nome}>
              <div>
                <span className="lp-vitrine-nome">{prato.nome}</span>
                <span className="suave pequeno">{formatarReais(prato.preco)}</span>
              </div>
              {r ? (
                <div className="lp-vitrine-dir">
                  <span className="pequeno">
                    sobra <strong>{formatarReais(r.conta.sobra)}</strong> · {formatarPct(r.diagnostico.margem_delivery)}
                  </span>
                  <SemaforoSelo semaforo={r.diagnostico.semaforo} />
                </div>
              ) : (
                <div className="lp-vitrine-dir">
                  <span className="suave pequeno">sem número</span>
                  <SemaforoSelo semaforo={null} rotulo="Sem receita" />
                </div>
              )}
            </li>
          ))}
        </ul>
      </div>
      <figcaption className="suave pequeno">Exemplo com a lanchonete fictícia da demo. Sobra e margem no delivery.</figcaption>
    </figure>
  )
}
