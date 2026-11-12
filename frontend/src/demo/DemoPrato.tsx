import { useEffect, useState } from 'react'
import type { Diagnostico, Ingrediente } from '../api'
import { Carregando } from '../componentes/Carregando'
import { ContaPedido } from '../componentes/ContaPedido'
import { EditorFicha } from '../componentes/EditorFicha'
import { Etiqueta } from '../componentes/Etiqueta'
import { NumerosDiagnostico } from '../componentes/NumerosDiagnostico'
import { SemaforoSelo } from '../componentes/SemaforoSelo'
import { novaChave, textoEscrito, validarLinhas, type LinhaFicha as LinhaEdicao } from '../fichaLinhas'
import { formatarPct, formatarQuantidade, formatarReais, lerPreco, numeroParaCampo, precoParaCampo } from '../formato'
import { custoPorUnidade, diasEntre, precoAntigo, PRECO_ANTIGO_DIAS } from './calculosDemo'
import type { PratoNaDemo } from './Demo'
import {
  diagnosticoDemo,
  FICHAS_GRAVADAS,
  HOJE_DEMO,
  ingrediente,
  INGREDIENTES_DEMO,
  MEDIDAS_EXEMPLO,
  PRATOS_LIDOS,
  RESTAURANTE_DEMO,
  type LinhaFicha,
  type ResultadoDemo,
} from './dadosDemo'
import { ORIGEM_GRAVACAO } from './DemoFoto'

// O EditorFicha do app recebe o cadastro no formato da API; aqui ele vem do cadastro fictício.
const CADASTRO: Ingrediente[] = INGREDIENTES_DEMO.map((i) => ({
  id: i.id,
  nome: i.nome,
  unidade: i.unidade,
  preco_embalagem: i.preco_embalagem,
  quantidade_embalagem: i.quantidade_embalagem,
  custo_por_unidade: custoPorUnidade(i.preco_embalagem, i.quantidade_embalagem).texto(4),
}))

type Modo = 'texto' | 'lendo' | 'revisao' | 'pronto'

/** Diagnóstico da demo no formato que o NumerosDiagnostico do app já sabe mostrar. */
function comoDiagnostico(r: ResultadoDemo): Diagnostico {
  return {
    semaforo: r.diagnostico.semaforo,
    pendente: null,
    mensagem: null,
    custo: r.diagnostico.custo,
    margem_balcao_pct: r.diagnostico.margem_balcao,
    margem_delivery_pct: r.diagnostico.margem_delivery,
    preco_sugerido_delivery: r.diagnostico.preco_sugerido_delivery,
    conta: r.conta,
  }
}

export function DemoPrato({
  prato,
  fichaSalva,
  atrasoMs,
  onSalvar,
  onVoltar,
}: {
  prato: PratoNaDemo
  fichaSalva: LinhaFicha[] | null
  atrasoMs: number
  onSalvar: (linhas: LinhaFicha[]) => void
  onVoltar: () => void
}) {
  const gravada = FICHAS_GRAVADAS.find((f) => f.prato === PRATOS_LIDOS[prato.origem].nome)!
  const [modo, setModo] = useState<Modo>(fichaSalva ? 'pronto' : 'texto')
  const [linhas, setLinhas] = useState<LinhaEdicao[]>([])
  const [tentou, setTentou] = useState(false)
  const [conferi, setConferi] = useState(false)

  useEffect(() => {
    if (modo !== 'lendo') return
    const t = setTimeout(() => {
      setLinhas(
        gravada.itens.map((item) => ({
          chave: novaChave(),
          ingrediente: item.ingrediente?.id ?? null,
          quantidade: numeroParaCampo(item.quantidade),
          nomeLido: item.nome_lido,
          escrito: textoEscrito(item.quantidade_lida, item.unidade_lida),
          quantidadeLida: item.quantidade_lida,
          medidaLida: item.unidade_lida,
          motivos: item.motivos as LinhaEdicao['motivos'],
          estimativa:
            item.estimativa ??
            (item.motivos.includes('sem_quantidade') && item.quantidade !== null
              ? `O texto não dizia quanto; o sistema assumiu ${formatarQuantidade(item.quantidade, item.unidade)}. Confira.`
              : undefined),
        })),
      )
      setModo('revisao')
    }, atrasoMs)
    return () => clearTimeout(t)
  }, [modo, atrasoMs, gravada])

  const { problemas, itens } = validarLinhas(linhas)
  const marcadas = linhas.filter((l) => l.motivos.some((m) => m !== 'nome_diferente' && m !== 'medida_salva')).length

  function preencherExemplo() {
    setLinhas((atual) =>
      atual.map((l) => {
        const medida = l.ingrediente ? MEDIDAS_EXEMPLO[l.ingrediente] : undefined
        if (l.quantidade || !medida) return l
        return { ...l, quantidade: numeroParaCampo(String(Number(l.quantidadeLida ?? '1') * Number(medida.quantidade))) }
      }),
    )
  }

  function confirmar() {
    setTentou(true)
    if (!itens || (marcadas > 0 && !conferi)) return
    onSalvar(itens.map((i) => ({ ingrediente: i.ingrediente, quantidade: i.quantidade })))
    setModo('pronto')
  }

  return (
    <div className="pilha">
      <button type="button" className="botao botao-texto voltar demo-voltar" onClick={onVoltar}>
        ← Painel
      </button>
      <div>
        <h3>
          {prato.nome} · {prato.preco ? formatarReais(prato.preco) : 'sem preço'}
        </h3>
      </div>

      {modo === 'texto' && (
        <>
          <div className="campo">
            <label htmlFor="demo-texto">O que vai neste prato (escrito do jeito do dono)</label>
            <textarea id="demo-texto" rows={3} readOnly value={gravada.texto} />
            <span className="suave pequeno">Na demo o texto é fixo, porque a resposta da IA foi gravada para ele.</span>
          </div>
          <button type="button" className="botao botao-primario" onClick={() => setModo('lendo')}>
            Organizar com a IA
          </button>
        </>
      )}

      {modo === 'lendo' && (
        <>
          <Carregando titulo="Organizando a receita…" detalhe="A IA liga cada item ao seu cadastro. As contas ficam com o sistema." />
          <p className="demo-centro">
            <Etiqueta origem={ORIGEM_GRAVACAO}>Resultado gravado de uma leitura real</Etiqueta>
          </p>
        </>
      )}

      {modo === 'revisao' && (
        <>
          <div className="aviso aviso-atencao">
            A IA leu “{gravada.texto}”. Os itens destacados precisam de você: confira o ingrediente e informe quanto dá cada medida
            caseira.
          </div>
          <EditorFicha
            linhas={linhas}
            setLinhas={setLinhas}
            cadastro={CADASTRO}
            mostrarProblemas={tentou}
            problemas={problemas}
            onCadastrar={() => Promise.reject(new Error('Na demo o cadastro de ingredientes é fixo.'))}
          />
          <button type="button" className="botao botao-texto" onClick={preencherExemplo}>
            Sem tempo? Preencher as medidas com o exemplo (1 fatia de queijo prato = 18 g)
          </button>
          {marcadas > 0 && (
            <label className="confirmacao">
              <input type="checkbox" checked={conferi} onChange={(e) => setConferi(e.target.checked)} />
              Conferi os itens destacados
            </label>
          )}
          {tentou && (!itens || (marcadas > 0 && !conferi)) && (
            <div className="aviso aviso-erro" role="alert">
              {!itens ? 'Corrija as linhas marcadas antes de salvar.' : 'Marque que conferiu os itens destacados.'}
            </div>
          )}
          <button type="button" className="botao botao-primario" onClick={confirmar}>
            Confirmar receita
          </button>
        </>
      )}

      {modo === 'pronto' && fichaSalva && <Diagnostico prato={prato} ficha={fichaSalva} />}
    </div>
  )
}

function Diagnostico({ prato, ficha }: { prato: PratoNaDemo; ficha: LinhaFicha[] }) {
  if (!prato.preco) {
    return <div className="aviso aviso-info">Sem preço não há conta: volte à revisão e informe o preço deste prato.</div>
  }
  const r = diagnosticoDemo(prato.preco, ficha)
  const antigos = ficha
    .map((l) => ingrediente(l.ingrediente))
    .filter((i) => precoAntigo(i.atualizado_em, HOJE_DEMO))
  return (
    <div className="pilha">
      <div className="cartao pilha">
        <div className="linha">
          <SemaforoSelo semaforo={r.diagnostico.semaforo} />
          <span className="suave pequeno">pela margem no delivery</span>
        </div>
        <NumerosDiagnostico diagnostico={comoDiagnostico(r)} margemDesejada={RESTAURANTE_DEMO.margem_desejada_pct} mostrarConta embalagemNaReceita />
      </div>

      {antigos.length > 0 && (
        <div className="aviso aviso-atencao pilha-curta">
          <span><Etiqueta origem="Funciona na demo; ainda não está no app real.">Em desenvolvimento</Etiqueta></span>
          {antigos.map((i) => (
            <span key={i.id}>
              O preço de <strong>{i.nome}</strong> é de {i.atualizado_em.split('-').reverse().join('/')}, há{' '}
              {diasEntre(i.atualizado_em, HOJE_DEMO)} dias sem atualizar (mais de {PRECO_ANTIGO_DIAS}). A conta pode estar
              desatualizada.
            </span>
          ))}
        </div>
      )}

      <Simulador prato={prato} ficha={ficha} atual={r} />
    </div>
  )
}

/** Em desenvolvimento: testar um preço novo e ver a sobra e o farol mudarem. */
function Simulador({ prato, ficha, atual }: { prato: PratoNaDemo; ficha: LinhaFicha[]; atual: ResultadoDemo }) {
  const inicial = atual.diagnostico.preco_sugerido_delivery ?? (Number(prato.preco) + 2).toFixed(2)
  const [texto, setTexto] = useState(precoParaCampo(inicial))
  const lido = lerPreco(texto)
  const novo = lido.ok && lido.valor && Number(lido.valor) > 0 ? diagnosticoDemo(lido.valor, ficha) : null
  return (
    <section className="cartao pilha demo-em-dev" aria-labelledby="demo-simulador">
      <span><Etiqueta origem="Funciona na demo; no app real será um parâmetro no diagnóstico, com a conta no Python.">Em desenvolvimento</Etiqueta></span>
      <h4 id="demo-simulador">Testar outro preço</h4>
      <div className={`campo${lido.ok ? '' : ' campo-invalido'}`}>
        <label htmlFor="demo-sim-preco">E se eu cobrar (R$)</label>
        <input id="demo-sim-preco" inputMode="decimal" value={texto} onChange={(e) => setTexto(e.target.value)} />
        {!lido.ok && <span className="campo-erro">{lido.erro}</span>}
      </div>
      {novo && (
        <>
          <div className="linha">
            <SemaforoSelo semaforo={novo.diagnostico.semaforo} />
            <span>
              sobra <strong>{formatarReais(novo.conta.sobra)}</strong> por pedido · margem {formatarPct(novo.diagnostico.margem_delivery)}
              <span className="suave"> (hoje: {formatarReais(atual.conta.sobra)})</span>
            </span>
          </div>
          <ContaPedido conta={novo.conta} titulo={`Com o preço de ${formatarReais(novo.conta.preco)}`} embalagemNaReceita />
        </>
      )}
      <p className="suave pequeno" style={{ margin: 0 }}>
        Preço mais alto pode reduzir as vendas. O LucraFood mostra a conta; quantos pedidos você perderia, ele não prevê.
      </p>
    </section>
  )
}
