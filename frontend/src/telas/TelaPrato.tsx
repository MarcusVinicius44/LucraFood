import { useEffect, useState } from 'react'
import { Link, Navigate, useParams } from 'react-router-dom'
import {
  ErroApi,
  atualizarPrato,
  buscarFicha,
  buscarPrato,
  buscarRestaurante,
  confirmarFichaTexto,
  criarIngrediente,
  lerFichaTexto,
  listarIngredientes,
  listarPratos,
  salvarFicha,
  type FichaDoPrato,
  type Ingrediente,
  type PratoDados,
  type PratoPainel,
  type Restaurante,
} from '../api'
import { restauranteSalvo } from '../armazenamento'
import { Carregando } from '../componentes/Carregando'
import { ConversaFicha } from '../componentes/ConversaFicha'
import { EditorFicha } from '../componentes/EditorFicha'
import { novaChave, textoEscrito, validarLinhas, type LinhaFicha } from '../fichaLinhas'
import { NumerosDiagnostico } from '../componentes/NumerosDiagnostico'
import { SemaforoSelo } from '../componentes/SemaforoSelo'
import {
  formatarQuantidade,
  formatarReais,
  lerNumero,
  lerPreco,
  numeroParaCampo,
  precoParaCampo,
  resumoDaFicha,
} from '../formato'

const TEXTO_MAX = 1000 // igual a ia_ficha.TEXTO_MAX

type Modo = 'ver' | 'texto' | 'revisao' | 'manual'

const msgErro = (e: unknown, padrao: string) => (e instanceof ErroApi ? e.message : padrao)

export function TelaPrato() {
  const { id } = useParams()
  const pratoId = Number(id)
  const salvo = restauranteSalvo()
  const [prato, setPrato] = useState<PratoDados | null>(null)
  const [ficha, setFicha] = useState<FichaDoPrato | null>(null)
  const [cadastro, setCadastro] = useState<Ingrediente[]>([])
  const [restaurante, setRestaurante] = useState<Restaurante | null>(null)
  const [outros, setOutros] = useState<PratoPainel[]>([])
  const [erro, setErro] = useState<string | null>(null)

  useEffect(() => {
    if (!salvo || !Number.isInteger(pratoId)) return
    setPrato(null)
    setFicha(null)
    setErro(null)
    Promise.all([buscarPrato(pratoId), buscarFicha(pratoId), listarIngredientes(salvo.id), buscarRestaurante(salvo.id), listarPratos(salvo.id)])
      .then(([p, f, i, r, lista]) => {
        setPrato(p)
        setFicha(f)
        setCadastro(i)
        setRestaurante(r)
        setOutros(lista)
      })
      .catch((e: unknown) => setErro(msgErro(e, 'Erro inesperado ao carregar o prato.')))
  }, [pratoId, salvo?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!salvo) return <Navigate to="/foto" replace />
  if (erro) return <div className="aviso aviso-erro" role="alert">{erro}</div>
  if (!prato || !ficha || !restaurante) return <Carregando titulo="Carregando o prato…" />

  // Próximo prato sem ficha (prioriza os que já têm preço: dão diagnóstico assim que a ficha fica pronta).
  const semFicha = outros.filter((p) => p.id !== pratoId && p.ficha_itens === 0)
  const proximo = semFicha.find((p) => p.preco_venda) ?? semFicha[0]

  async function cadastrarIngrediente(dados: Parameters<typeof criarIngrediente>[1]) {
    const criado = await criarIngrediente(salvo!.id, dados)
    setCadastro((c) => [...c, criado].sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR')))
    return criado
  }

  return (
    <div className="pilha">
      <Link className="voltar" to="/painel">← Painel</Link>
      <div className="prato-painel-topo">
        <div>
          <h1 style={{ marginBottom: '0.25rem' }}>{prato.nome}</h1>
          <div className="suave pequeno">
            {prato.categoria ? `${prato.categoria} · ` : ''}
            {resumoDaFicha(ficha.ficha_itens, ficha.ficha_confirmada_em)}
          </div>
        </div>
        <SemaforoSelo semaforo={ficha.diagnostico.semaforo} />
      </div>

      <section className="cartao pilha-curta">
        <h2>Diagnóstico</h2>
        <NumerosDiagnostico diagnostico={ficha.diagnostico} margemDesejada={restaurante.margem_desejada_pct} />
      </section>

      <DadosDoPrato
        key={pratoId}
        prato={prato}
        onSalvo={async (p) => {
          setPrato(p)
          setFicha(await buscarFicha(pratoId)) // preço, embalagem e rendimento mudam o diagnóstico
        }}
      />

      <FichaDoPratoCartao
        key={pratoId}
        pratoId={pratoId}
        ficha={ficha}
        cadastro={cadastro}
        onCadastrar={cadastrarIngrediente}
        onSalva={(f) => {
          setFicha(f)
          setOutros((l) => l.map((p) => (p.id === pratoId ? { ...p, ficha_itens: f.ficha_itens } : p)))
        }}
        proximo={proximo}
      />
    </div>
  )
}

// --- Preço, embalagem e rendimento ------------------------------------------

function DadosDoPrato({ prato, onSalvo }: { prato: PratoDados; onSalvo: (p: PratoDados) => Promise<void> }) {
  const [preco, setPreco] = useState(precoParaCampo(prato.preco_venda))
  const [embalagem, setEmbalagem] = useState(precoParaCampo(prato.custo_embalagem))
  const [rendimento, setRendimento] = useState(numeroParaCampo(prato.rendimento))
  const [enviando, setEnviando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const [ok, setOk] = useState(false)

  const precoLido = lerPreco(preco)
  const embalagemLida = lerNumero(embalagem, 2, { permitirZero: true })
  const rendimentoLido = lerNumero(rendimento, 2)
  const erros = {
    preco: precoLido.ok ? null : precoLido.erro,
    embalagem: embalagemLida.ok ? null : embalagemLida.erro,
    rendimento: !rendimentoLido.ok ? rendimentoLido.erro : rendimentoLido.valor === null ? 'Informe as porções (1 se for um prato só)' : null,
  }
  const mudou =
    preco !== precoParaCampo(prato.preco_venda) ||
    embalagem !== precoParaCampo(prato.custo_embalagem) ||
    rendimento !== numeroParaCampo(prato.rendimento)

  async function salvar(e: React.FormEvent) {
    e.preventDefault()
    if (enviando || erros.preco || erros.embalagem || erros.rendimento) return
    setEnviando(true)
    setErro(null)
    setOk(false)
    try {
      const p = await atualizarPrato(prato.id, {
        preco_venda: (precoLido as { valor: string | null }).valor,
        custo_embalagem: (embalagemLida as { valor: string | null }).valor ?? '0',
        rendimento: (rendimentoLido as { valor: string }).valor,
      })
      await onSalvo(p)
      setOk(true)
    } catch (e) {
      setErro(msgErro(e, 'Erro inesperado ao salvar.'))
    } finally {
      setEnviando(false)
    }
  }

  return (
    <form className="cartao pilha" onSubmit={salvar} noValidate>
      <h2>Preço e porção</h2>
      <div className="grade-3">
        <div className={`campo${erros.preco ? ' campo-invalido' : ''}`}>
          <label htmlFor="preco">Preço de venda (R$)</label>
          <input id="preco" inputMode="decimal" value={preco} onChange={(e) => { setPreco(e.target.value); setOk(false) }} placeholder="Sem preço" />
          {erros.preco && <span className="campo-erro">{erros.preco}</span>}
        </div>
        <div className={`campo${erros.embalagem ? ' campo-invalido' : ''}`}>
          <label htmlFor="embalagem">Embalagem (R$)</label>
          <input id="embalagem" inputMode="decimal" value={embalagem} onChange={(e) => { setEmbalagem(e.target.value); setOk(false) }} placeholder="0,00" />
          {erros.embalagem ? <span className="campo-erro">{erros.embalagem}</span> : <span className="suave pequeno">Marmita, sacola… por porção</span>}
        </div>
        <div className={`campo${erros.rendimento ? ' campo-invalido' : ''}`}>
          <label htmlFor="rendimento">Porções da receita</label>
          <input id="rendimento" inputMode="decimal" value={rendimento} onChange={(e) => { setRendimento(e.target.value); setOk(false) }} />
          {erros.rendimento ? <span className="campo-erro">{erros.rendimento}</span> : <span className="suave pequeno">Bolo inteiro = 12 fatias</span>}
        </div>
      </div>
      {erro && <div className="aviso aviso-erro" role="alert">{erro}</div>}
      <div className="linha">
        <button className="botao botao-primario" type="submit" disabled={enviando || !mudou}>
          {enviando ? 'Salvando…' : 'Salvar'}
        </button>
        {ok && <span className="suave pequeno" role="status">Salvo.</span>}
      </div>
    </form>
  )
}

// --- Ficha técnica ------------------------------------------------------------

function FichaDoPratoCartao({
  pratoId,
  ficha,
  cadastro,
  onCadastrar,
  onSalva,
  proximo,
}: {
  pratoId: number
  ficha: FichaDoPrato
  cadastro: Ingrediente[]
  onCadastrar: (dados: Parameters<typeof criarIngrediente>[1]) => Promise<Ingrediente>
  onSalva: (f: FichaDoPrato) => void
  proximo?: PratoPainel
}) {
  const [modo, setModo] = useState<Modo>('ver')
  const [texto, setTexto] = useState('')
  const [linhas, setLinhasEstado] = useState<LinhaFicha[]>([])
  const [lendo, setLendo] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const [tentou, setTentou] = useState(false)
  const [conferi, setConferi] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const [acabouDeSalvar, setAcabouDeSalvar] = useState(false)

  const setLinhas = (f: (a: LinhaFicha[]) => LinhaFicha[]) => setLinhasEstado(f)
  const { problemas, itens } = validarLinhas(linhas)
  const marcadas = linhas.filter((l) => l.motivos.length > 0).length

  function abrirManual() {
    setLinhasEstado(
      ficha.itens.length
        ? ficha.itens.map((i) => ({ chave: novaChave(), ingrediente: i.ingrediente, quantidade: numeroParaCampo(i.quantidade), motivos: [] }))
        : [{ chave: novaChave(), ingrediente: null, quantidade: '', motivos: [] }],
    )
    iniciar('manual')
  }

  function iniciar(m: Modo) {
    setModo(m)
    setErro(null)
    setTentou(false)
    setConferi(false)
    setAcabouDeSalvar(false)
  }

  async function lerTexto() {
    if (lendo || !texto.trim()) return
    setLendo(true)
    setErro(null)
    try {
      const lido = await lerFichaTexto(pratoId, texto.trim())
      setLinhasEstado(
        lido.itens.map((item) => ({
          chave: novaChave(),
          ingrediente: item.ingrediente?.id ?? null,
          quantidade: numeroParaCampo(item.quantidade),
          nomeLido: item.nome_lido,
          escrito: textoEscrito(item.quantidade_lida, item.unidade_lida),
          quantidadeLida: item.quantidade_lida,
          medidaLida: item.unidade_lida,
          unidadeLida: item.ingrediente ? null : item.unidade,
          motivos: item.motivos,
          // "pão" sem número: o Python assume 1 unidade e marca para conferir.
          estimativa:
            item.motivos.includes('sem_quantidade') && item.quantidade !== null
              ? `O texto não dizia quanto; o sistema assumiu ${formatarQuantidade(item.quantidade, item.unidade)}. Confira.`
              : undefined,
        })),
      )
      iniciar('revisao')
    } catch (e) {
      setErro(msgErro(e, 'Erro inesperado ao ler a receita.'))
    } finally {
      setLendo(false)
    }
  }

  async function salvar() {
    setTentou(true)
    if (enviando || !itens || (modo === 'revisao' && marcadas > 0 && !conferi)) return
    setEnviando(true)
    setErro(null)
    try {
      const f = modo === 'revisao' ? await confirmarFichaTexto(pratoId, itens) : await salvarFicha(pratoId, itens)
      onSalva(f)
      setModo('ver')
      setTexto('')
      setAcabouDeSalvar(true)
    } catch (e) {
      setErro(msgErro(e, 'Erro inesperado ao salvar a ficha.'))
    } finally {
      setEnviando(false)
    }
  }

  return (
    <section className="cartao pilha">
      <div className="linha" style={{ justifyContent: 'space-between' }}>
        <h2 style={{ margin: 0 }}>Ficha técnica</h2>
        {modo === 'ver' && ficha.itens.length > 0 && (
          <span className="suave pequeno">{resumoDaFicha(ficha.ficha_itens, ficha.ficha_confirmada_em)}</span>
        )}
      </div>

      {modo === 'ver' && (
        <>
          {acabouDeSalvar && (
            <div className="aviso aviso-sucesso pilha-curta" role="status">
              <span>Ficha salva. O diagnóstico acima já está atualizado.</span>
              {proximo && (
                <Link className="botao botao-primario botao-pequeno" to={`/pratos/${proximo.id}`}>
                  Próximo prato sem ficha: {proximo.nome} →
                </Link>
              )}
            </div>
          )}
          {ficha.itens.length === 0 ? (
            <p className="suave">
              Ainda sem ficha. Escreva a receita do jeito que você fala (ex.: “pão, 150 g de carne, 2 fatias de queijo”) e a IA
              monta a lista; você confere antes de salvar.
            </p>
          ) : (
            <>
              <ul className="lista-ficha">
                {ficha.itens.map((i) => (
                  <li key={i.ingrediente}>
                    <span>{i.nome}</span>
                    <span className="suave">{formatarQuantidade(i.quantidade, i.unidade)}</span>
                    <span className="numero-valor">{formatarReais(i.custo)}</span>
                  </li>
                ))}
              </ul>
              <p className="pequeno suave" style={{ margin: 0 }}>
                Custo da receita (só ingredientes): <strong>{formatarReais(ficha.custo_receita)}</strong>
                {Number(ficha.rendimento) !== 1 && ` · rende ${numeroParaCampo(ficha.rendimento)} porções`}
              </p>
              <p className="pequeno suave" style={{ margin: 0 }}>Esqueceu algum ingrediente? A ficha incompleta deixa o custo menor do que é.</p>
            </>
          )}
          <div className="linha">
            <button className="botao botao-primario" onClick={() => iniciar('texto')}>
              {ficha.itens.length ? 'Reescrever a receita (IA)' : 'Escrever a receita (IA)'}
            </button>
            <button className="botao botao-secundario" onClick={abrirManual}>
              {ficha.itens.length ? 'Editar à mão' : 'Montar à mão'}
            </button>
          </div>
        </>
      )}

      {modo === 'texto' && (
        <div className="pilha">
          <div className="campo">
            <label htmlFor="receita">O que vai em uma receita deste prato, e quanto</label>
            <textarea
              id="receita"
              rows={5}
              maxLength={TEXTO_MAX}
              value={texto}
              onChange={(e) => setTexto(e.target.value)}
              placeholder="Ex.: 1 pão de hambúrguer, 150 g de carne moída, 2 fatias de queijo, 20 g de alface"
              disabled={lendo}
            />
            <span className="suave pequeno">{texto.length}/{TEXTO_MAX} · A IA só lê; quem converte unidades e calcula é o sistema.</span>
          </div>
          {ficha.itens.length > 0 && (
            <div className="aviso aviso-info">Ao confirmar, a ficha atual ({ficha.itens.length} ingredientes) será substituída.</div>
          )}
          {erro && <div className="aviso aviso-erro" role="alert">{erro}</div>}
          {lendo ? (
            <Carregando titulo="Lendo a receita…" detalhe="Leva alguns segundos." />
          ) : (
            <div className="linha">
              <button className="botao botao-primario" onClick={lerTexto} disabled={!texto.trim()}>Ler receita</button>
              <button className="botao botao-texto" onClick={() => iniciar('ver')}>Cancelar</button>
            </div>
          )}
        </div>
      )}

      {(modo === 'revisao' || modo === 'manual') && (
        <div className="pilha">
          {modo === 'revisao' && (
            <p className="suave" style={{ margin: 0 }}>
              Confira o que a IA leu. {marcadas > 0 ? `${marcadas} ${marcadas === 1 ? 'item precisa' : 'itens precisam'} da sua atenção (destacados).` : 'Nada ficou em dúvida.'}
            </p>
          )}
          {modo === 'revisao' && <ConversaFicha pratoId={pratoId} linhas={linhas} setLinhas={setLinhas} />}
          <EditorFicha
            linhas={linhas}
            setLinhas={setLinhas}
            cadastro={cadastro}
            mostrarProblemas={tentou}
            problemas={problemas}
            onCadastrar={onCadastrar}
          />
          {modo === 'revisao' && marcadas > 0 && (
            <label className="confirmacao">
              <input type="checkbox" checked={conferi} onChange={(e) => setConferi(e.target.checked)} />
              Conferi os itens destacados
            </label>
          )}
          {tentou && !itens && <div className="aviso aviso-erro" role="alert">Corrija as linhas marcadas antes de salvar.</div>}
          {tentou && itens && modo === 'revisao' && marcadas > 0 && !conferi && (
            <div className="aviso aviso-atencao" role="alert">Marque “Conferi os itens destacados” para salvar.</div>
          )}
          {erro && <div className="aviso aviso-erro" role="alert">{erro}</div>}
          <div className="linha">
            <button className="botao botao-primario" onClick={salvar} disabled={enviando || linhas.length === 0}>
              {enviando ? 'Salvando…' : modo === 'revisao' ? 'Confirmar ficha' : 'Salvar ficha'}
            </button>
            <button className="botao botao-texto" onClick={() => iniciar('ver')}>Cancelar</button>
          </div>
        </div>
      )}
    </section>
  )
}
