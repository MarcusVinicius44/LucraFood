import { SemaforoSelo } from '../componentes/SemaforoSelo'
import { diagnosticoDemo, fichaExemplo, PRATOS_LIDOS } from '../demo/dadosDemo'
import foto from '../demo/fixtures/cardapio-sabor-da-esquina.png'
import { formatarReais, precoParaCampo } from '../formato'
import { usePassoAtivo } from './hooks'

// "Como funciona" contado pela rolagem: no computador a tela fica parada e muda conforme os passos passam;
// no celular cada passo traz a própria tela, empilhada.
const PASSOS = [
  {
    titulo: 'Tire uma foto do cardápio',
    texto: 'A IA lê os nomes e os preços. Preço que ela não consegue ler fica em branco, nunca é chutado.',
  },
  {
    titulo: 'Confira e corrija',
    texto: 'Você vê a lista e ajusta o que quiser. Nada é salvo antes de você confirmar.',
  },
  {
    titulo: 'Diga o que vai em cada prato e veja o farol',
    texto: 'Escreva do seu jeito ("pão, 150 g de carne, 2 fatias de queijo"). O LucraFood faz a conta e acende o farol de cada prato.',
  },
]

const AMOSTRA = ['X-Burger', 'X-Bacon', 'Batata Frita', 'Refrigerante Lata'].map((n) => PRATOS_LIDOS.find((p) => p.nome === n) ?? PRATOS_LIDOS[0])
const FAROL = ['X-Burger', 'X-Bacon', 'Batata Frita'].map((nome) => {
  const p = PRATOS_LIDOS.find((x) => x.nome === nome)!
  return { nome, r: diagnosticoDemo(p.preco!, fichaExemplo(nome)!) }
})

function Tela({ n }: { n: number }) {
  return (
    <div className={`cf-tela cf-tela-${n}`} aria-hidden="true">
      <span className="cf-tela-rotulo">TELA 0{n + 1}/03</span>
      {n === 0 && (
        <div className="cf-foto">
          <img src={foto} alt="" width={540} height={720} loading="lazy" />
          <span className="cena-scan" />
        </div>
      )}
      {n === 1 && (
        <ul className="cf-revisao">
          {AMOSTRA.map((p, i) => (
            <li key={p.nome} className={i === 1 ? 'cf-destaque' : ''}>
              <span>{p.nome}</span>
              <span className="cf-campo">R$ {precoParaCampo(p.preco)}</span>
            </li>
          ))}
          <li className="cf-botao">Confirmar e ver o painel</li>
        </ul>
      )}
      {n === 2 && (
        <ul className="cf-farol">
          {FAROL.map(({ nome, r }) => (
            <li key={nome}>
              <span>
                <strong>{nome}</strong>
                <small>sobra {formatarReais(r.conta.sobra)}</small>
              </span>
              <SemaforoSelo semaforo={r.diagnostico.semaforo} />
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export function ComoFunciona() {
  const [ref, ativo] = usePassoAtivo<HTMLDivElement>('.cf-passo')
  return (
    <div ref={ref} className="cf">
      <ol className="cf-passos">
        {PASSOS.map((p, i) => (
          <li key={p.titulo} className={`cf-passo${ativo === i ? ' ativo' : ''}`}>
            <span className="cf-num">0{i + 1}</span>
            <h3>{p.titulo}</h3>
            <p>{p.texto}</p>
            <div className="cf-tela-inline">
              <Tela n={i} />
            </div>
          </li>
        ))}
      </ol>
      <div className="cf-visual">
        <div className="cf-visual-fixo">
          {PASSOS.map((p, i) => (
            <div key={p.titulo} className={`cf-camada${ativo === i ? ' ativa' : ''}`}>
              <Tela n={i} />
            </div>
          ))}
          <div className="cf-pontos" aria-hidden="true">
            {PASSOS.map((p, i) => (
              <span key={p.titulo} className={ativo === i ? 'ativo' : ''} />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
