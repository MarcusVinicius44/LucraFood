import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ErroApi, confirmarCardapio, type PratoExtraido } from '../api'
import { rascunho, restauranteSalvo, salvarRascunho, salvarRestaurante } from '../armazenamento'
import { Etiqueta } from '../componentes/Etiqueta'
import { chaveDoNome, lerPreco, precoParaCampo } from '../formato'

interface Linha {
  id: number
  nome: string
  categoria: string
  descricao: string | null
  preco: string // como o dono digita ("24,90")
  precoIlegivel: boolean // a IA não conseguiu ler o preço na foto
}

let proximoId = 1
const novaLinha = (p?: PratoExtraido): Linha => ({
  id: proximoId++,
  nome: p?.nome ?? '',
  categoria: p?.categoria ?? '',
  descricao: p?.descricao ?? null,
  preco: precoParaCampo(p?.preco ?? null),
  precoIlegivel: p ? p.preco === null : false,
})

type Conflito = { mensagem: string; pratos: string[] }

export function TelaRevisao() {
  const navegar = useNavigate()
  const salvo = restauranteSalvo()
  const [linhas, setLinhas] = useState<Linha[]>(() => (rascunho() ?? []).map((p) => novaLinha(p)))
  const [restaurante, setRestaurante] = useState(salvo?.nome ?? '')
  const [enviando, setEnviando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const [conflito, setConflito] = useState<Conflito | null>(null)

  // Problemas de cada linha, recalculados a cada digitação.
  const problemas = useMemo(() => {
    const contagem = new Map<string, number>()
    linhas.forEach((l) => {
      const chave = chaveDoNome(l.nome)
      if (chave) contagem.set(chave, (contagem.get(chave) ?? 0) + 1)
    })
    return new Map(
      linhas.map((l) => {
        const preco = lerPreco(l.preco)
        return [
          l.id,
          {
            nome: !l.nome.trim() ? 'Dê um nome ao prato' : (contagem.get(chaveDoNome(l.nome)) ?? 0) > 1 ? 'Prato repetido na lista' : null,
            preco: preco.ok ? null : preco.erro,
          },
        ]
      }),
    )
  }, [linhas])

  const temProblema = [...problemas.values()].some((p) => p.nome || p.preco)
  const semPreco = linhas.filter((l) => !l.preco.trim()).length

  function alterar(id: number, campo: 'nome' | 'categoria' | 'preco', valor: string) {
    setLinhas((atual) => atual.map((l) => (l.id === id ? { ...l, [campo]: valor } : l)))
  }

  function remover(id: number) {
    setLinhas((atual) => atual.filter((l) => l.id !== id))
  }

  function tirarJaSalvos() {
    if (!conflito) return
    const chaves = new Set(conflito.pratos.map(chaveDoNome))
    setLinhas((atual) => atual.filter((l) => !chaves.has(chaveDoNome(l.nome))))
    setConflito(null)
  }

  async function confirmar() {
    if (enviando || temProblema || !restaurante.trim() || linhas.length === 0) return
    setEnviando(true) // desativa o botão já no primeiro clique
    setErro(null)
    setConflito(null)
    const pratos: PratoExtraido[] = linhas.map((l) => {
      const preco = lerPreco(l.preco)
      return {
        nome: l.nome.trim(),
        categoria: l.categoria.trim() || null,
        descricao: l.descricao,
        preco: preco.ok ? preco.valor : null,
      }
    })
    try {
      const r = await confirmarCardapio(restaurante.trim(), pratos)
      salvarRestaurante({ id: r.restaurante_id, nome: restaurante.trim() })
      salvarRascunho(null)
      navegar('/painel', { replace: true }) // "voltar" não reabre a revisão já salva
    } catch (e) {
      const falha = e instanceof ErroApi ? e : new ErroApi(0, 'Erro inesperado ao salvar.')
      if (falha.status === 409) {
        // O restaurante existe; lembra dele para o painel funcionar mesmo assim.
        const id = falha.dados.restaurante_id
        if (typeof id === 'number') salvarRestaurante({ id, nome: restaurante.trim() })
        const repetidos = Array.isArray(falha.dados.pratos) ? (falha.dados.pratos as string[]) : []
        setConflito({ mensagem: falha.message, pratos: repetidos })
      } else {
        setErro(falha.message)
      }
      setEnviando(false) // só reativa em caso de erro, para o dono corrigir
    }
  }

  if (linhas.length === 0 && rascunho() === null) {
    return (
      <div className="cartao pilha">
        <h1>Nada para revisar</h1>
        <p className="suave">Fotografe um cardápio para a IA ler os pratos.</p>
        <Link className="botao botao-primario" to="/foto">Fotografar cardápio</Link>
      </div>
    )
  }

  return (
    <div className="pilha">
      <div>
        <div className="linha">
          <h1>Confira os pratos</h1>
          <Etiqueta origem="Nomes e preços lidos da foto pela IA. Podem ter erro de leitura.">lido pela IA</Etiqueta>
        </div>
        <p className="suave">
          A IA leu {linhas.length} {linhas.length === 1 ? 'prato' : 'pratos'} da foto. Corrija o que estiver errado: nada é salvo até você confirmar.
        </p>
      </div>

      <div className="cartao">
        <div className="campo">
          <label htmlFor="restaurante">Nome do restaurante</label>
          <input
            id="restaurante"
            value={restaurante}
            readOnly={!!salvo}
            onChange={(e) => setRestaurante(e.target.value)}
            placeholder="Ex.: Lanchonete da Ana"
          />
          {salvo && <span className="suave pequeno">Os pratos entram no restaurante que você já usa.</span>}
        </div>
      </div>

      {semPreco > 0 && (
        <div className="aviso aviso-atencao">
          {semPreco === 1 ? '1 prato está' : `${semPreco} pratos estão`} sem preço. Preencha, ou deixe em branco: o prato fica salvo, mas sem semáforo até ter preço.
        </div>
      )}

      {conflito && (
        <div className="aviso aviso-erro pilha" role="alert">
          <p>{conflito.mensagem}</p>
          {conflito.pratos.length > 0 && <p><strong>{conflito.pratos.join(', ')}</strong></p>}
          <div className="linha">
            <button className="botao botao-secundario" onClick={tirarJaSalvos}>Tirar estes da lista</button>
            <Link className="botao botao-texto" to="/painel">Ver o painel</Link>
          </div>
        </div>
      )}
      {erro && <div className="aviso aviso-erro" role="alert">{erro}</div>}

      <div className="pilha">
        {linhas.map((l) => {
          const p = problemas.get(l.id)!
          return (
            <div key={l.id} className={`prato-revisao${!l.preco.trim() ? ' sem-preco' : ''}`}>
              <div className="prato-revisao-campos">
                <div className={`campo${p.nome ? ' campo-invalido' : ''}`}>
                  <label htmlFor={`nome-${l.id}`}>Prato</label>
                  <input id={`nome-${l.id}`} value={l.nome} onChange={(e) => alterar(l.id, 'nome', e.target.value)} />
                  {p.nome && <span className="campo-erro">{p.nome}</span>}
                </div>
                <div className="campo">
                  <label htmlFor={`cat-${l.id}`}>Categoria</label>
                  <input id={`cat-${l.id}`} value={l.categoria} onChange={(e) => alterar(l.id, 'categoria', e.target.value)} />
                </div>
                <div className={`campo${p.preco ? ' campo-invalido' : ''}`}>
                  <label htmlFor={`preco-${l.id}`}>Preço (R$)</label>
                  <input
                    id={`preco-${l.id}`}
                    inputMode="decimal"
                    value={l.preco}
                    placeholder={l.precoIlegivel ? 'ilegível' : '0,00'}
                    onChange={(e) => alterar(l.id, 'preco', e.target.value)}
                  />
                  {p.preco && <span className="campo-erro">{p.preco}</span>}
                </div>
              </div>
              <div className="linha" style={{ justifyContent: 'space-between' }}>
                <span className="suave pequeno">{l.precoIlegivel ? 'A IA não conseguiu ler o preço deste prato.' : ''}</span>
                <button className="botao botao-texto" onClick={() => remover(l.id)}>Remover</button>
              </div>
            </div>
          )
        })}
        <button className="botao botao-secundario" onClick={() => setLinhas((a) => [...a, novaLinha()])}>
          + Adicionar prato
        </button>
      </div>

      <div className="barra-fixa">
        <div className="barra-fixa-conteudo">
          <Link className="botao botao-texto" to="/foto">Outra foto</Link>
          <button
            className="botao botao-primario"
            onClick={confirmar}
            disabled={enviando || temProblema || !restaurante.trim() || linhas.length === 0}
          >
            {enviando ? 'Salvando…' : `Confirmar ${linhas.length} ${linhas.length === 1 ? 'prato' : 'pratos'}`}
          </button>
        </div>
      </div>
    </div>
  )
}
