import { useEffect, useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import {
  ErroApi,
  buscarRestaurante,
  listarIngredientes,
  listarPratos,
  type PratoPainel,
  type Restaurante,
  type Semaforo,
} from '../api'
import { esquecerRestaurante, restauranteSalvo } from '../armazenamento'
import { Carregando } from '../componentes/Carregando'
import { NumerosDiagnostico } from '../componentes/NumerosDiagnostico'
import { ProximosPassos } from '../componentes/ProximosPassos'
import { SemaforoSelo } from '../componentes/SemaforoSelo'
import { formatarPct, formatarReais, resumoDaFicha } from '../formato'

type Filtro = Semaforo | 'pendente' | null

const FILTROS: { valor: Semaforo | 'pendente'; semaforo: Semaforo | null }[] = [
  { valor: 'vermelho', semaforo: 'vermelho' },
  { valor: 'amarelo', semaforo: 'amarelo' },
  { valor: 'verde', semaforo: 'verde' },
  { valor: 'pendente', semaforo: null },
]

const tipoDoPrato = (p: PratoPainel): Semaforo | 'pendente' => p.semaforo ?? 'pendente'

export function TelaPainel() {
  const salvo = restauranteSalvo()
  const [restaurante, setRestaurante] = useState<Restaurante | null>(null)
  const [pratos, setPratos] = useState<PratoPainel[] | null>(null)
  const [totalIngredientes, setTotalIngredientes] = useState(0)
  const [erro, setErro] = useState<ErroApi | null>(null)
  const [filtro, setFiltro] = useState<Filtro>(null)
  const navegar = useNavigate()

  useEffect(() => {
    if (!salvo) return
    Promise.all([buscarRestaurante(salvo.id), listarPratos(salvo.id), listarIngredientes(salvo.id)])
      .then(([r, p, i]) => {
        setRestaurante(r)
        setPratos(p)
        setTotalIngredientes(i.length)
      })
      .catch((e: unknown) => setErro(e instanceof ErroApi ? e : new ErroApi(0, 'Erro inesperado ao carregar o painel.')))
  }, [salvo?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!salvo) return <Navigate to="/app/foto" replace />
  if (erro?.status === 404) {
    // O navegador lembra um restaurante que não existe mais no banco (ex.: banco recriado).
    return (
      <div className="cartao pilha">
        <h1>Restaurante não encontrado</h1>
        <p className="suave">O restaurante guardado neste navegador não existe mais no sistema. Comece de novo pela foto do cardápio.</p>
        <button
          className="botao botao-primario"
          onClick={() => {
            esquecerRestaurante()
            navegar('/app/foto', { replace: true })
          }}
        >
          Começar de novo
        </button>
      </div>
    )
  }
  if (erro) return <div className="aviso aviso-erro" role="alert">{erro.message}</div>
  if (!restaurante || !pratos) return <Carregando titulo="Carregando o painel…" />

  if (pratos.length === 0) {
    return (
      <div className="cartao pilha">
        <h1>{restaurante.nome}</h1>
        <p className="suave">Ainda não há pratos salvos. Fotografe o cardápio para começar.</p>
        <Link className="botao botao-primario" to="/app/foto">Fotografar cardápio</Link>
      </div>
    )
  }

  const contagem = (tipo: Semaforo | 'pendente') => pratos.filter((p) => tipoDoPrato(p) === tipo).length
  const semFicha = pratos.filter((p) => p.ficha_itens === 0).length
  const semPreco = pratos.filter((p) => !p.preco_venda).length
  const visiveis = filtro ? pratos.filter((p) => tipoDoPrato(p) === filtro) : pratos

  // Agrupa por categoria, mantendo a ordem que vem do backend (categoria, nome).
  const grupos = new Map<string, PratoPainel[]>()
  visiveis.forEach((p) => {
    const cat = p.categoria || 'Sem categoria'
    grupos.set(cat, [...(grupos.get(cat) ?? []), p])
  })

  return (
    <div className="pilha">
      <div>
        <h1>{restaurante.nome}</h1>
        <p className="suave">{pratos.length} {pratos.length === 1 ? 'prato' : 'pratos'} no cardápio.</p>
      </div>

      <ProximosPassos restaurante={restaurante} pratos={pratos} totalIngredientes={totalIngredientes} />

      <div className="resumo" role="group" aria-label="Filtrar pratos pelo semáforo">
        {FILTROS.map(({ valor, semaforo }) => (
          <button
            key={valor}
            className="resumo-item"
            aria-pressed={filtro === valor}
            onClick={() => setFiltro(filtro === valor ? null : valor)}
          >
            <span className="resumo-numero">{contagem(valor)}</span>
            <SemaforoSelo semaforo={semaforo} />
          </button>
        ))}
      </div>

      {semFicha > 0 && (
        <div className="aviso aviso-atencao">
          <strong>{semFicha} de {pratos.length} pratos</strong> ainda sem ficha técnica. Sem ficha não dá para saber o custo, então
          esses pratos ficam sem semáforo e sem números.
        </div>
      )}
      {semPreco > 0 && (
        <div className="aviso aviso-info">
          {semPreco === 1 ? '1 prato está' : `${semPreco} pratos estão`} sem preço de venda.
        </div>
      )}

      <p className="suave pequeno">
        Calculado pelo sistema com a sua ficha técnica e as taxas do restaurante: delivery {formatarPct(restaurante.taxa_delivery_pct)},
        impostos {formatarPct(restaurante.impostos_pct)}, margem desejada {formatarPct(restaurante.margem_desejada_pct)},
        mínima {formatarPct(restaurante.margem_minima_pct)}. A IA não faz nenhuma conta. <Link to="/app/ajustes">Mudar taxas</Link>
      </p>

      {visiveis.length === 0 && <p className="suave">Nenhum prato neste filtro.</p>}

      {[...grupos].map(([categoria, lista]) => (
        <section key={categoria}>
          <h2 className="categoria-titulo">{categoria}</h2>
          <div className="pilha">
            {lista.map((p) => (
              <CartaoPrato key={p.id} prato={p} margemDesejada={restaurante.margem_desejada_pct} />
            ))}
          </div>
        </section>
      ))}

      <Link className="botao botao-secundario" to="/app/foto">Adicionar pratos por foto</Link>
    </div>
  )
}

const ACAO_PENDENTE: Record<string, string> = {
  sem_preco: 'Informar preço',
  sem_ficha: 'Montar ficha',
  configuracao: 'Ver prato',
}

function CartaoPrato({ prato, margemDesejada }: { prato: PratoPainel; margemDesejada: string }) {
  return (
    <Link to={`/app/pratos/${prato.id}`} className="cartao prato-painel cartao-link">
      <div className="prato-painel-topo">
        <div>
          <div className="prato-painel-nome">{prato.nome}</div>
          <div className="suave pequeno">
            {prato.preco_venda ? formatarReais(prato.preco_venda) : 'Sem preço'} · {resumoDaFicha(prato.ficha_itens, prato.ficha_confirmada_em)}
          </div>
        </div>
        <SemaforoSelo semaforo={prato.semaforo} />
      </div>
      <NumerosDiagnostico diagnostico={prato} margemDesejada={margemDesejada} />
      {prato.pendente && <span className="link-acao">{ACAO_PENDENTE[prato.pendente]} →</span>}
    </Link>
  )
}
