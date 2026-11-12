import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import logoBranco from '../assets/lucrafood-logo-branco.svg'
import { AUTOR, LINKEDIN, NUMEROS_PROJETO, REPOSITORIO } from './conteudo'
import { Diagrama } from './Diagrama'
import './landing.css'

/** /por-dentro: a parte técnica, fora da página de venda, para quem quer ver a engenharia. */
export function PorDentro() {
  useEffect(() => {
    document.title = 'Por dentro do LucraFood'
    window.scrollTo(0, 0)
    return () => {
      document.title = 'LucraFood'
    }
  }, [])
  return (
    <div className="lp lp-escuro-pagina">
      <header className="lp-cabecalho">
        <div className="lp-cabecalho-conteudo">
          <Link to="/" aria-label="LucraFood, página inicial">
            <img src={logoBranco} alt="LucraFood" height={28} />
          </Link>
          <Link className="lp-nav-voltar" to="/">← Voltar para o site</Link>
        </div>
      </header>
      <main className="lp-tecnico">
        <div className="lp-conteudo">
          <p className="lp-sobretitulo">Por dentro do LucraFood</p>
          <h1>Para quem quer ver a engenharia</h1>
          <p className="lp-tecnico-intro">
            A IA lê a foto e o texto; o Python faz todas as contas; nada é gravado sem a revisão do dono. Cada número abaixo vem de
            uma rodada real de avaliação com gabarito, com a saída guardada no repositório.
          </p>

          <div className="lp-tecnico-grade">
            <div>
              <h2>O fluxo</h2>
              <Diagrama />
            </div>
            <div className="pilha">
              <div>
                <h2>Avaliado com dados reais e gabarito</h2>
                <ul className="lp-numeros-projeto">
                  {NUMEROS_PROJETO.map((n) => (
                    <li key={n.valor + n.texto}>
                      <strong>{n.valor}</strong> <span>{n.texto}</span>
                    </li>
                  ))}
                </ul>
                <p className="lp-nota">
                  Cada rodada chama a API de verdade e a saída fica guardada em{' '}
                  <a href={`${REPOSITORIO}/tree/main/evals`}>evals/</a>. Histórico em{' '}
                  <a href={`${REPOSITORIO}/blob/main/docs/AVALIACAO.md`}>docs/AVALIACAO.md</a>.
                </p>
              </div>
              <div>
                <h2>Por que troquei o Groq pelo Gemini</h2>
                <p>
                  O plano grátis do Groq limita ~1.000 tokens de saída por minuto, e o JSON de um cardápio grande passa disso: só 3
                  de 8 fotos completaram, mesmo dividindo a foto em faixas. Com o Gemini 3.5 Flash-Lite, 8 de 8.
                </p>
              </div>
            </div>
          </div>

          <div className="lp-tecnico-grade">
            <div>
              <h2>Decisões de engenharia</h2>
              <ul className="lp-lista-tecnica">
                <li><strong>Dois passos:</strong> extrair não salva nada; só o "confirmar" grava, depois da revisão humana.</li>
                <li>
                  <strong>Códigos HTTP certos:</strong> 422 para foto ilegível (pede outra foto), 429 e 503 do provedor com novas
                  tentativas e espera, 502 se a IA devolver JSON inválido duas vezes.
                </li>
                <li><strong>Cardápio confirmado duas vezes</strong> (clique duplo, "voltar") devolve 409 e não duplica pratos.</li>
                <li><strong>Rendimento da receita:</strong> bolo que rende 12 fatias divide o custo dos ingredientes, não o da embalagem.</li>
                <li><strong>Toda conta em <code>Decimal</code></strong>, em um só módulo testado; o LLM nunca calcula.</li>
                <li>
                  <strong>Ficha em conversa:</strong> o Python escolhe a pergunta e faz a conta; a IA só lê a resposta ("uns 2
                  quilos", "pula essa").
                </li>
                <li>
                  <strong>A demo desta página não chama a API:</strong> usa respostas reais gravadas e uma cópia das contas em
                  TypeScript, testada contra o Python.
                </li>
              </ul>
            </div>
            <div>
              <h2>Stack</h2>
              <ul className="lp-lista-tecnica">
                <li>Django 5.2 + Django REST Framework</li>
                <li>React 19 + TypeScript + Vite</li>
                <li>Gemini pela biblioteca <code>openai</code> (API compatível), Pydantic para validar a saída</li>
              </ul>
              <div className="lp-acoes">
                <a className="botao botao-claro" href={REPOSITORIO} target="_blank" rel="noopener noreferrer">GitHub</a>
                <a className="botao lp-botao-contorno" href={`${REPOSITORIO}#readme`} target="_blank" rel="noopener noreferrer">README</a>
                <a className="botao lp-botao-contorno" href={`${REPOSITORIO}/tree/main/evals`} target="_blank" rel="noopener noreferrer">evals/</a>
              </div>
            </div>
          </div>
        </div>
      </main>
      <footer className="lp-rodape">
        <div className="lp-conteudo lp-rodape-linha">
          <span>© 2026 LucraFood · Criado por <a href={LINKEDIN} target="_blank" rel="noopener noreferrer">{AUTOR}</a></span>
          <Link to="/">Página inicial</Link>
        </div>
      </footer>
    </div>
  )
}
