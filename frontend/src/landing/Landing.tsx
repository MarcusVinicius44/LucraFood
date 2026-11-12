import { lazy, Suspense, useEffect, type ReactNode } from 'react'
import logo from '../assets/lucrafood-logo.svg'
import logoBranco from '../assets/lucrafood-logo-branco.svg'
import { Etiqueta } from '../componentes/Etiqueta'
import { SemaforoSelo } from '../componentes/SemaforoSelo'
import { Diagrama } from './Diagrama'
import {
  AUTOR,
  CONTATO_EMAIL,
  CONTATO_WHATSAPP,
  FONTES,
  fonte,
  LINKEDIN,
  NUMEROS_MERCADO,
  NUMEROS_PROJETO,
  REPOSITORIO,
} from './conteudo'
import { Vitrine } from './Vitrine'
import './landing.css'

// A demo é a parte mais pesada da página: só baixa quando o visitante chega perto dela.
const Demo = lazy(() => import('../demo/Demo'))

/** Mostra as seções com uma entrada suave quando aparecem na tela (só CSS + IntersectionObserver). */
function useRevelar() {
  useEffect(() => {
    const alvos = Array.from(document.querySelectorAll('.lp-revelar'))
    if (!('IntersectionObserver' in window)) {
      alvos.forEach((a) => a.classList.add('lp-visivel'))
      return
    }
    const obs = new IntersectionObserver(
      (entradas) =>
        entradas.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add('lp-visivel')
            obs.unobserve(e.target)
          }
        }),
      { rootMargin: '0px 0px -10% 0px' },
    )
    alvos.forEach((a) => obs.observe(a))
    return () => obs.disconnect()
  }, [])
}

function Secao({ id, className = '', children, rotulo }: { id: string; className?: string; children: ReactNode; rotulo?: string }) {
  return (
    <section id={id} className={`lp-secao ${className}`} aria-labelledby={rotulo}>
      <div className="lp-conteudo lp-revelar">{children}</div>
    </section>
  )
}

function Icone({ nome }: { nome: 'foto' | 'conferir' | 'farol' | 'ia' | 'etiqueta' | 'aviso' }) {
  const caminhos: Record<string, ReactNode> = {
    foto: (
      <>
        <path d="M4 8h3l2-3h6l2 3h3v11H4z" />
        <circle cx="12" cy="13" r="3.5" />
      </>
    ),
    conferir: (
      <>
        <path d="M5 4h11l3 3v13H5z" />
        <path d="M8.5 13l2.5 2.5L16 10" />
      </>
    ),
    farol: (
      <>
        <rect x="8" y="3" width="8" height="18" rx="3" />
        <circle cx="12" cy="7.5" r="1.4" />
        <circle cx="12" cy="12" r="1.4" />
        <circle cx="12" cy="16.5" r="1.4" />
      </>
    ),
    ia: (
      <>
        <path d="M4 12h4l2-5 4 10 2-5h4" />
      </>
    ),
    etiqueta: (
      <>
        <path d="M3 12V4h8l10 10-8 8z" />
        <circle cx="7.5" cy="8.5" r="1.3" />
      </>
    ),
    aviso: (
      <>
        <path d="M12 4l9 16H3z" />
        <path d="M12 10v4M12 17.5v.01" />
      </>
    ),
  }
  return (
    <svg className="lp-icone" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {caminhos[nome]}
    </svg>
  )
}

function Fonte({ id }: { id: string }) {
  const f = fonte(id)
  return (
    <p className="lp-fonte">
      Fonte: <a href={f.url} target="_blank" rel="noopener noreferrer">{f.quem}</a>
    </p>
  )
}

export function Landing() {
  useRevelar()
  return (
    <div className="lp">
      <a className="lp-pular" href="#conteudo">Pular para o conteúdo</a>
      <header className="lp-cabecalho">
        <div className="lp-cabecalho-conteudo">
          <a href="#topo" aria-label="LucraFood, topo da página">
            <img src={logo} alt="LucraFood" height={30} />
          </a>
          <nav aria-label="Seções">
            <a href="#como-funciona">Como funciona</a>
            <a href="#demo">Demo</a>
            <a href="#por-dentro">Por dentro</a>
          </nav>
        </div>
      </header>

      <main id="conteudo">
        {/* 1. Topo */}
        <section id="topo" className="lp-topo">
          <div className="lp-conteudo lp-topo-grade">
            <div className="lp-topo-texto">
              <p className="lp-sobretitulo">Para restaurantes que vendem por app de delivery</p>
              <h1>Quanto sobra de cada prato depois da taxa do app?</h1>
              <p className="lp-subtitulo">
                Tire uma foto do cardápio. O LucraFood lê os pratos com IA, você confere, e ele mostra prato a prato quanto fica pra
                você no delivery.
              </p>
              <div className="lp-acoes">
                <a className="botao botao-primario" href="#demo">Testar a demo</a>
                <a className="botao botao-secundario" href={REPOSITORIO} target="_blank" rel="noopener noreferrer">
                  Ver o código no GitHub
                </a>
              </div>
            </div>
            <Vitrine />
          </div>
        </section>

        {/* 2. O problema */}
        <Secao id="problema" rotulo="problema-titulo">
          <p className="lp-sobretitulo">O problema</p>
          <h2 id="problema-titulo">O delivery cresceu. A conta ficou mais difícil.</h2>
          <ul className="lp-grade-numeros">
            {NUMEROS_MERCADO.map((n) => (
              <li key={n.valor} className="lp-numero-mercado">
                <span className="lp-numero-valor">{n.valor}</span>
                <p>{n.texto}</p>
                <Fonte id={n.fonte} />
              </li>
            ))}
          </ul>
          <p className="lp-fechamento">
            Muitos donos sabem o preço de venda. Poucos sabem quanto sobra depois de ingredientes, embalagem, imposto e taxa do app.
          </p>
        </Secao>

        {/* 3. Como funciona */}
        <Secao id="como-funciona" className="lp-secao-clara" rotulo="como-titulo">
          <p className="lp-sobretitulo">Como funciona</p>
          <h2 id="como-titulo">Três passos, e quem decide é você</h2>
          <ol className="lp-passos">
            <li>
              <Icone nome="foto" />
              <span className="lp-passo-num">1</span>
              <h3>Foto do cardápio</h3>
              <p>A IA lê os nomes e os preços. Preço que ela não consegue ler fica em branco, nunca é chutado.</p>
            </li>
            <li>
              <Icone nome="conferir" />
              <span className="lp-passo-num">2</span>
              <h3>Você confere e corrige</h3>
              <p>Nada é salvo antes de você confirmar a lista.</p>
            </li>
            <li>
              <Icone nome="farol" />
              <span className="lp-passo-num">3</span>
              <h3>Diga o que vai em cada prato</h3>
              <p>
                Escreva do seu jeito ("pão, 150 g de carne, 2 fatias de queijo"). O LucraFood mostra quanto sobra e o farol:
              </p>
              <p className="linha">
                <SemaforoSelo semaforo="verde" />
                <SemaforoSelo semaforo="amarelo" />
                <SemaforoSelo semaforo="vermelho" />
              </p>
            </li>
          </ol>
        </Secao>

        {/* 4. Demo */}
        <section id="demo" className="lp-secao lp-secao-demo" aria-labelledby="demo-titulo">
          <div className="lp-conteudo">
            <p className="lp-sobretitulo">Demo interativa</p>
            <h2 id="demo-titulo">Teste com o cardápio de uma lanchonete de exemplo</h2>
            <p className="suave">
              Menos de 1 minuto. A lanchonete é fictícia e as respostas da IA foram gravadas de uma leitura real, então a demo não
              gasta nada e nada sai do seu navegador.
            </p>
            <Suspense fallback={<p className="suave">Carregando a demo…</p>}>
              <Demo />
            </Suspense>
          </div>
        </section>

        {/* 5. Benefícios (só o que já existe no app real) */}
        <Secao id="beneficios" rotulo="beneficios-titulo">
          <p className="lp-sobretitulo">O que muda para o restaurante</p>
          <h2 id="beneficios-titulo">O que o LucraFood já faz hoje</h2>
          <ul className="lp-lista-beneficios">
            <li>
              <strong>Ver quais pratos dão pouco lucro no delivery.</strong> O painel separa os pratos em saudável, atenção e
              crítico pela margem depois da taxa do app.
            </li>
            <li>
              <strong>Ver a conta inteira, linha por linha:</strong> preço − ingredientes − embalagem − imposto − taxa do app = o
              que sobra.
            </li>
            <li>
              <strong>Saber o custo de cada ingrediente da receita</strong>, inclusive de receitas que rendem várias porções.
            </li>
            <li>
              <strong>Um preço sugerido</strong> para chegar na margem que você escolheu, sempre marcado como sugestão.
            </li>
          </ul>
        </Secao>

        {/* 6. Por que confiar */}
        <Secao id="confianca" className="lp-secao-clara" rotulo="confianca-titulo">
          <p className="lp-sobretitulo">Por que confiar</p>
          <h2 id="confianca-titulo">A IA ajuda. Quem faz a conta é o sistema.</h2>
          <ul className="lp-confianca">
            <li>
              <Icone nome="ia" />
              <p><strong>A IA lê, você confere, o sistema calcula.</strong> A IA nunca faz conta.</p>
            </li>
            <li>
              <Icone nome="etiqueta" />
              <p><strong>Tudo que é estimativa vem marcado como estimativa.</strong> Sugestão de preço também.</p>
            </li>
            <li>
              <Icone nome="aviso" />
              <p>
                <strong>O sistema avisa o que ainda não sabe</strong>, como pratos sem receita ou sem preço, em vez de mostrar um
                número bonito e errado.
              </p>
            </li>
          </ul>
        </Secao>

        {/* 7. O que vem por aí */}
        <Secao id="em-breve" rotulo="breve-titulo">
          <p className="lp-sobretitulo">O que vem por aí</p>
          <h2 id="breve-titulo">Em desenvolvimento, já dá para testar na demo</h2>
          <ul className="lp-grade-breve">
            <li className="cartao">
              <Etiqueta origem="Funciona na demo; ainda não está no app real.">Em desenvolvimento</Etiqueta>
              <h3>Testar um preço novo</h3>
              <p>Mude o preço e veja a sobra e o farol mudarem antes de mexer no app de delivery.</p>
            </li>
            <li className="cartao">
              <Etiqueta origem="Funciona na demo; ainda não está no app real.">Em desenvolvimento</Etiqueta>
              <h3>Ingrediente ficou mais caro</h3>
              <p>A carne subiu? Veja quais pratos foram afetados e quanto a sobra de cada um caiu.</p>
            </li>
            <li className="cartao">
              <Etiqueta origem="Funciona na demo; ainda não está no app real.">Em desenvolvimento</Etiqueta>
              <h3>Preço de ingrediente antigo</h3>
              <p>Aviso quando um preço está há mais de 30 dias sem atualizar: a conta pode estar desatualizada.</p>
            </li>
          </ul>
        </Secao>

        {/* 8. Planos */}
        <Secao id="planos" className="lp-secao-clara" rotulo="planos-titulo">
          <div className="cartao lp-planos">
            <Etiqueta origem="Ainda não existe plano pago.">Em breve</Etiqueta>
            <h2 id="planos-titulo">Planos</h2>
            <p>
              O LucraFood está em fase de validação com restaurantes. Ainda não há plano nem pagamento. Quer ser avisado quando
              abrir, ou testar no seu restaurante?
            </p>
            <div className="lp-acoes">
              <a className="botao botao-primario" href={CONTATO_EMAIL}>Quero ser avisado</a>
              <a className="botao botao-secundario" href={CONTATO_WHATSAPP} target="_blank" rel="noopener noreferrer">
                Falar no WhatsApp
              </a>
            </div>
          </div>
        </Secao>

        {/* 9. Por dentro */}
        <section id="por-dentro" className="lp-secao lp-tecnico" aria-labelledby="dentro-titulo">
          <div className="lp-conteudo lp-revelar">
            <p className="lp-sobretitulo">Por dentro do LucraFood</p>
            <h2 id="dentro-titulo">Para quem quer ver a engenharia</h2>
            <div className="lp-tecnico-grade">
              <div>
                <h3>O fluxo</h3>
                <Diagrama />
              </div>
              <div className="pilha">
                <div>
                  <h3>Avaliado com dados reais e gabarito</h3>
                  <ul className="lp-numeros-projeto">
                    {NUMEROS_PROJETO.map((n) => (
                      <li key={n.valor + n.texto}>
                        <strong>{n.valor}</strong> <span>{n.texto}</span>
                      </li>
                    ))}
                  </ul>
                  <p className="lp-nota">
                    Cada rodada chama a API de verdade e a saída fica guardada em <a href={`${REPOSITORIO}/tree/main/evals`}>evals/</a>.
                    Histórico em <a href={`${REPOSITORIO}/blob/main/docs/AVALIACAO.md`}>docs/AVALIACAO.md</a>.
                  </p>
                </div>
                <div>
                  <h3>Por que troquei o Groq pelo Gemini</h3>
                  <p>
                    O plano grátis do Groq limita ~1.000 tokens de saída por minuto, e o JSON de um cardápio grande passa disso:
                    só 3 de 8 fotos completaram, mesmo dividindo a foto em faixas. Com o Gemini 3.5 Flash-Lite, 8 de 8.
                  </p>
                </div>
              </div>
            </div>
            <div className="lp-tecnico-grade">
              <div>
                <h3>Decisões de engenharia</h3>
                <ul className="lp-lista-tecnica">
                  <li><strong>Dois passos:</strong> extrair não salva nada; só o "confirmar" grava, depois da revisão humana.</li>
                  <li>
                    <strong>Códigos HTTP certos:</strong> 422 para foto ilegível (pede outra foto), 429 e 503 do provedor com novas
                    tentativas e espera, 502 se a IA devolver JSON inválido duas vezes.
                  </li>
                  <li><strong>Cardápio confirmado duas vezes</strong> (clique duplo, "voltar") devolve 409 e não duplica pratos.</li>
                  <li><strong>Rendimento da receita:</strong> bolo que rende 12 fatias divide o custo dos ingredientes, não o da embalagem.</li>
                  <li><strong>Toda conta em <code>Decimal</code></strong>, em um só módulo testado; o LLM nunca calcula.</li>
                </ul>
              </div>
              <div>
                <h3>Stack</h3>
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
        </section>
      </main>

      {/* 10. Rodapé */}
      <footer className="lp-rodape">
        <div className="lp-conteudo">
          <img src={logoBranco} alt="LucraFood" height={28} />
          <p>Projeto de portfólio de {AUTOR}.</p>
          <p className="linha">
            <a href={REPOSITORIO} target="_blank" rel="noopener noreferrer">GitHub</a>
            <a href={LINKEDIN} target="_blank" rel="noopener noreferrer">LinkedIn</a>
          </p>
          <h2 className="lp-rodape-titulo">Fontes</h2>
          <ol className="lp-rodape-fontes">
            {FONTES.map((f) => (
              <li key={f.id}>
                <a href={f.url} target="_blank" rel="noopener noreferrer">{f.titulo}</a> — {f.quem}.
              </li>
            ))}
          </ol>
        </div>
      </footer>
    </div>
  )
}
