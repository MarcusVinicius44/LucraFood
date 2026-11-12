import { SemaforoSelo } from '../componentes/SemaforoSelo'
import { diagnosticoDemo, fichaExemplo, PRATOS_LIDOS, RESTAURANTE_DEMO } from '../demo/dadosDemo'
import foto from '../demo/fixtures/cardapio-sabor-da-esquina.png'
import { formatarPct, formatarReais } from '../formato'
import { useContador, useLinhaDoTempo, useVisivel } from './hooks'

// Cena do topo: o celular lê o cardápio, o painel monta os pratos e a sobra conta até o valor.
// Os números são os mesmos da demo (calculosDemo.ts, cópia testada do calculos.py), não imagem retocada.
const NOMES = ['X-Burger', 'X-Bacon', 'Batata Frita', 'X-Salada']

const LINHAS = NOMES.map((nome) => {
  const prato = PRATOS_LIDOS.find((p) => p.nome === nome)!
  const ficha = fichaExemplo(nome)
  const r = ficha && prato.preco ? diagnosticoDemo(prato.preco, ficha) : null
  return { prato, r }
})
const PRINCIPAL = LINHAS[0].r!
const BACON = LINHAS[1]
const ROTULO_SEMAFORO = { verde: 'Saudável', amarelo: 'Atenção', vermelho: 'Crítico' } as const

// Fases: 0 lendo · 1–4 pratos entram · 5 sobra conta · 6 chips (segura e recomeça)
const FASES = 7

export function CenaTopo() {
  const [ref, visivel] = useVisivel<HTMLDivElement>('0px')
  const fase = useLinhaDoTempo(FASES, 900, 6000, visivel)
  const sobra = useContador(Number(PRINCIPAL.conta.sobra), fase >= 5, 1100)

  return (
    <div ref={ref} className={`cena cena-fase-${fase}`} role="img" aria-label={`Exemplo do LucraFood: o celular lê o cardápio e o painel mostra quanto sobra de cada prato no delivery. No X-Burger de ${formatarReais(PRINCIPAL.conta.preco)}, sobram ${formatarReais(PRINCIPAL.conta.sobra)}.`}>
      <div className="cena-janela" aria-hidden="true">
        <div className="cena-janela-barra">
          <span /><span /><span />
          <strong>Painel · {RESTAURANTE_DEMO.nome}</strong>
        </div>
        <ul className="cena-lista">
          {LINHAS.map(({ prato, r }, i) => (
            <li key={prato.nome} className={fase >= i + 1 ? 'entrou' : ''}>
              <div>
                <span className="cena-nome">{prato.nome}</span>
                <span className="cena-preco">{formatarReais(prato.preco)}</span>
              </div>
              {r ? (
                <div className="cena-dir">
                  <span className="cena-margem">{formatarPct(r.diagnostico.margem_delivery)}</span>
                  <SemaforoSelo semaforo={r.diagnostico.semaforo} />
                </div>
              ) : (
                <div className="cena-dir">
                  <SemaforoSelo semaforo={null} rotulo="Sem receita" />
                </div>
              )}
            </li>
          ))}
        </ul>
        <div className={`cena-sobra${fase >= 5 ? ' entrou' : ''}`}>
          <span>Sobra no X-Burger, por pedido no app</span>
          <strong>{formatarReais(sobra.toFixed(2))}</strong>
        </div>
      </div>

      <div className="cena-celular" aria-hidden="true">
        <div className="cena-celular-tela">
          <img src={foto} alt="" width={540} height={720} />
          <span className="cena-scan" />
          <span className="cena-celular-status">{fase === 0 ? 'Lendo o cardápio…' : `${PRATOS_LIDOS.length} pratos lidos ✓`}</span>
        </div>
      </div>

      <span className={`cena-chip cena-chip-1${fase >= 6 ? ' entrou' : ''}`} aria-hidden="true">
        Taxa do app <strong>−{formatarReais(PRINCIPAL.conta.taxa_app)}</strong>
      </span>
      {BACON.r && (
        <span className={`cena-chip cena-chip-2 cena-chip-${BACON.r.diagnostico.semaforo}${fase >= 6 ? ' entrou' : ''}`} aria-hidden="true">
          {BACON.prato.nome}: <strong>{ROTULO_SEMAFORO[BACON.r.diagnostico.semaforo]}</strong>
        </span>
      )}
      <span className={`cena-chip cena-chip-3${fase >= 1 ? ' entrou' : ''}`} aria-hidden="true">
        Preço ilegível? Fica em branco
      </span>
    </div>
  )
}
