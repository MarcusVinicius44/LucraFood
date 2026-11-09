import { Link } from 'react-router-dom'
import type { PratoPainel, Restaurante } from '../api'

// Primeiro acesso: o dono só tem os pratos lidos da foto. Este cartão mostra o caminho até o
// diagnóstico de cada prato e leva direto ao próximo passo que falta. Some quando tudo está feito.

interface Passo {
  titulo: string
  detalhe: string
  feito: boolean
  link?: { para: string; texto: string }
}

export function ProximosPassos({
  restaurante,
  pratos,
  totalIngredientes,
}: {
  restaurante: Restaurante
  pratos: PratoPainel[]
  totalIngredientes: number
}) {
  const comFicha = pratos.filter((p) => p.ficha_itens > 0).length
  const comPreco = pratos.filter((p) => p.preco_venda).length
  const comSemaforo = pratos.filter((p) => p.semaforo).length
  // Prioriza o que dá diagnóstico mais rápido: prato com preço e sem ficha.
  const proximoSemFicha = pratos.find((p) => p.ficha_itens === 0 && p.preco_venda) ?? pratos.find((p) => p.ficha_itens === 0)
  const proximoSemPreco = pratos.find((p) => !p.preco_venda)
  const taxasInformadas = Number(restaurante.taxa_delivery_pct) > 0 || Number(restaurante.impostos_pct) > 0

  const passos: Passo[] = [
    {
      titulo: 'Cardápio lido',
      detalhe: `${pratos.length} ${pratos.length === 1 ? 'prato salvo' : 'pratos salvos'}`,
      feito: true,
    },
    {
      titulo: 'Taxas do delivery e impostos',
      detalhe: taxasInformadas
        ? 'informadas'
        : 'Quanto o app de delivery cobra e quanto vai de imposto. Sem isso a margem do delivery fica otimista.',
      feito: taxasInformadas,
      link: { para: '/ajustes', texto: 'Informar taxas' },
    },
    {
      titulo: 'Ingredientes que você compra',
      detalhe: totalIngredientes
        ? `${totalIngredientes} cadastrados (cadastre mais quando precisar)`
        : 'Cadastre o preço e o tamanho da embalagem de cada ingrediente. Dá para cadastrar também enquanto monta a ficha.',
      feito: totalIngredientes > 0,
      link: { para: '/ingredientes', texto: 'Cadastrar ingredientes' },
    },
    {
      titulo: 'Preço de venda de cada prato',
      detalhe: `${comPreco} de ${pratos.length} com preço`,
      feito: comPreco === pratos.length,
      link: proximoSemPreco ? { para: `/pratos/${proximoSemPreco.id}`, texto: `Informar preço: ${proximoSemPreco.nome}` } : undefined,
    },
    {
      titulo: 'Ficha técnica de cada prato',
      detalhe: `${comFicha} de ${pratos.length} com ficha. Escreva a receita em texto que a IA monta, você só confere.`,
      feito: comFicha === pratos.length,
      link: proximoSemFicha ? { para: `/pratos/${proximoSemFicha.id}`, texto: `Montar ficha: ${proximoSemFicha.nome}` } : undefined,
    },
    {
      titulo: 'Diagnóstico de lucro',
      detalhe: `${comSemaforo} de ${pratos.length} pratos com semáforo`,
      feito: comSemaforo === pratos.length,
    },
  ]

  if (passos.every((p) => p.feito)) return null
  const atual = passos.findIndex((p) => !p.feito)
  const feitos = passos.filter((p) => p.feito).length

  return (
    <section className="cartao passos" aria-labelledby="passos-titulo">
      <div className="linha" style={{ justifyContent: 'space-between' }}>
        <h2 id="passos-titulo" style={{ margin: 0 }}>Próximos passos</h2>
        <span className="suave pequeno">{feitos} de {passos.length}</span>
      </div>
      <div className="passos-barra" aria-hidden="true">
        <div style={{ width: `${(feitos / passos.length) * 100}%` }} />
      </div>
      <ol className="passos-lista">
        {passos.map((p, i) => (
          <li key={p.titulo} className={p.feito ? 'passo-feito' : i === atual ? 'passo-atual' : ''}>
            <span className="passo-marca" aria-hidden="true">{p.feito ? '✓' : i + 1}</span>
            <div>
              <strong>{p.titulo}</strong>
              <span className="sr-only">{p.feito ? ' (feito)' : ' (falta)'}</span>
              <div className="suave pequeno">{p.detalhe}</div>
              {!p.feito && p.link && (
                <Link className={`botao ${i === atual ? 'botao-primario' : 'botao-secundario'} botao-pequeno`} to={p.link.para}>
                  {p.link.texto}
                </Link>
              )}
            </div>
          </li>
        ))}
      </ol>
    </section>
  )
}
