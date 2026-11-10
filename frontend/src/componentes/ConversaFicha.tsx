import { useEffect, useRef, useState } from 'react'
import { ErroApi, conversarFicha, type ItemConversa, type PerguntaConversa, type RodadaConversa } from '../api'
import type { LinhaFicha } from '../fichaLinhas'
import { formatarQuantidade, lerNumero, numeroParaCampo } from '../formato'

// Ficha em conversa: o sistema pergunta o que faltou na leitura da receita ("quanto dá 1 fatia de
// queijo?") e o dono responde do jeito dele. Quem escolhe a pergunta e faz a conta é o backend
// (ia/conversa.py); a IA só lê a resposta. Nada é salvo aqui: as respostas preenchem as linhas
// abaixo, e o dono confirma a ficha como sempre.

type Fala = { quem: 'sistema' | 'dono'; texto: string }

const RESPOSTA_MAX = 200 // igual a ia_conversa.RESPOSTA_MAX

function paraItens(linhas: LinhaFicha[]): ItemConversa[] {
  return linhas.map((l) => {
    const q = lerNumero(l.quantidade, 3)
    return {
      chave: l.chave,
      nome_lido: l.nomeLido ?? '',
      ingrediente: l.ingrediente,
      quantidade: q.ok ? q.valor : null,
      quantidade_lida: l.quantidadeLida ?? null,
      unidade_lida: l.medidaLida ?? null,
      motivos: l.motivos,
    }
  })
}

function textoFinal(r: RodadaConversa): string {
  const partes = ['Pronto, não tenho mais perguntas. Confira a ficha abaixo e confirme.']
  if (r.pulados.length) {
    partes.push(r.pulados.length === 1 ? 'O item que você pulou ficou para preencher.' : 'Os itens que você pulou ficaram para preencher.')
  }
  if (r.sem_cadastro) {
    partes.push(
      r.sem_cadastro === 1
        ? '1 ingrediente não está no seu cadastro: use “Cadastrar” na linha dele.'
        : `${r.sem_cadastro} ingredientes não estão no seu cadastro: use “Cadastrar” na linha de cada um.`,
    )
  }
  return partes.join(' ')
}

export function ConversaFicha({
  pratoId,
  linhas,
  setLinhas,
}: {
  pratoId: number
  linhas: LinhaFicha[]
  setLinhas: (f: (atual: LinhaFicha[]) => LinhaFicha[]) => void
}) {
  const [falas, setFalas] = useState<Fala[]>([])
  const [pergunta, setPergunta] = useState<PerguntaConversa | null>(null)
  const [pulados, setPulados] = useState<number[]>([])
  const [resposta, setResposta] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const [comecou, setComecou] = useState(false) // houve ao menos uma pergunta
  const campo = useRef<HTMLInputElement>(null)

  // Primeira pergunta (sem IA). Sem nada a perguntar, a conversa nem aparece.
  useEffect(() => {
    conversarFicha(pratoId, { itens: paraItens(linhas), pulados: [] })
      .then((r) => {
        if (!r.pergunta) return
        setComecou(true)
        setPergunta(r.pergunta)
        setFalas([{ quem: 'sistema', texto: r.pergunta.texto }])
      })
      .catch(() => {}) // a revisão continua funcionando à mão
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Depois de cada rodada, o campo volta a ficar ativo: devolve o foco para a próxima resposta.
  useEffect(() => {
    if (!enviando && falas.length > 1 && pergunta) campo.current?.focus()
  }, [enviando]) // eslint-disable-line react-hooks/exhaustive-deps

  async function rodada(corpo: { pulados: number[]; resposta?: string }, falaDono: string) {
    if (!pergunta || enviando) return
    setEnviando(true)
    setErro(null)
    const anterior = pergunta
    try {
      const r = await conversarFicha(pratoId, {
        itens: paraItens(linhas),
        pulados: corpo.pulados,
        pergunta: corpo.resposta ? { chave: anterior.chave } : null,
        resposta: corpo.resposta ?? null,
      })
      const novas: Fala[] = [{ quem: 'dono', texto: falaDono }]
      if (r.atualizado) {
        const a = r.atualizado
        setLinhas((atual) =>
          atual.map((l) =>
            l.chave === a.chave
              ? {
                  ...l,
                  quantidade: numeroParaCampo(a.quantidade),
                  motivos: a.motivos,
                  estimativa: a.origem,
                  medidaEnsinada:
                    a.medida && l.ingrediente
                      ? { ingrediente: l.ingrediente, medida: a.medida.medida, quantidade: a.medida.quantidade }
                      : l.medidaEnsinada,
                }
              : l,
          ),
        )
        const anotei = `Anotei: ${a.origem.replace(' (você informou)', '')}.`
        novas.push({
          quem: 'sistema',
          texto: a.medida
            ? `${anotei} Quando você confirmar a ficha, vou lembrar que 1 ${a.medida.medida} de ${a.medida.nome} dá ${formatarQuantidade(a.medida.quantidade, a.unidade)}, para não perguntar de novo.`
            : anotei,
        })
      } else if (r.aviso) {
        novas.push({ quem: 'sistema', texto: r.aviso })
      } else if (r.pulados.includes(anterior.chave)) {
        novas.push({ quem: 'sistema', texto: 'Tudo bem, deixei esse em branco para você preencher.' })
      }
      if (r.pergunta && (r.pergunta.chave !== anterior.chave || !r.aviso)) novas.push({ quem: 'sistema', texto: r.pergunta.texto })
      if (!r.pergunta) novas.push({ quem: 'sistema', texto: textoFinal(r) })
      setFalas((f) => [...f, ...novas])
      setPergunta(r.pergunta)
      setPulados(r.pulados)
      setResposta('')
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : 'Erro inesperado. Tente de novo ou preencha a linha à mão.')
    } finally {
      setEnviando(false)
    }
  }

  if (!comecou) return null

  return (
    <div className="conversa pilha-curta" aria-live="polite">
      <div className="conversa-titulo">Faltou alguma coisa? Eu pergunto.</div>
      {falas.map((f, i) => (
        <div key={i} className={`balao balao-${f.quem}`}>{f.texto}</div>
      ))}
      {pergunta && (
        <form
          className="conversa-resposta"
          onSubmit={(e) => {
            e.preventDefault()
            const texto = resposta.trim()
            if (texto) rodada({ pulados, resposta: texto }, texto)
          }}
        >
          <input
            ref={campo}
            aria-label="Sua resposta"
            value={resposta}
            maxLength={RESPOSTA_MAX}
            onChange={(e) => setResposta(e.target.value)}
            placeholder="Ex.: uns 30 g"
            disabled={enviando}
          />
          <button className="botao botao-primario botao-pequeno" type="submit" disabled={enviando || !resposta.trim()}>
            {enviando ? 'Lendo…' : 'Responder'}
          </button>
          <button
            className="botao botao-texto botao-pequeno"
            type="button"
            disabled={enviando}
            onClick={() => rodada({ pulados: [...pulados, pergunta.chave] }, 'Pular')}
          >
            Pular
          </button>
        </form>
      )}
      {erro && <div className="aviso aviso-erro" role="alert">{erro}</div>}
      <span className="suave pequeno">A IA só lê sua resposta; a conta é feita pelo sistema. Você também pode preencher as linhas direto.</span>
    </div>
  )
}
