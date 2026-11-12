import { lazy, Suspense, type CSSProperties, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import logoBranco from '../assets/lucrafood-logo-branco.svg'
import { Etiqueta } from '../componentes/Etiqueta'
import { CenaTopo } from './CenaTopo'
import { ComoFunciona } from './ComoFunciona'
import {
  AUTOR,
  CONTAGEM_MERCADO,
  CONTATO_EMAIL,
  CONTATO_PILOTO,
  FONTES,
  fonte,
  LINKEDIN,
  NUMEROS_MERCADO,
  PERGUNTAS,
  PRATOS_GIRO,
  RECURSOS_FAIXA,
  REPOSITORIO,
  SEM_COM,
  type NumeroMercado,
} from './conteudo'
import { Cupom } from './Cupom'
import { useContador, useGiro, useRevelar, useVisivel } from './hooks'
import './landing.css'

// A demo é a parte mais pesada da página: só baixa quando o visitante chega perto dela.
const Demo = lazy(() => import('../demo/Demo'))

const atraso = (i: number) => ({ '--d': `${i * 90}ms` }) as CSSProperties

function BotaoPiloto({ children = 'Quero o piloto gratuito', className = '' }: { children?: ReactNode; className?: string }) {
  return (
    <a className={`botao lp-botao-cta ${className}`} href={CONTATO_PILOTO} target="_blank" rel="noopener noreferrer">
      <svg viewBox="0 0 24 24" aria-hidden="true" width="18" height="18">
        <path
          fill="currentColor"
          d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2Zm0 18.2a8.2 8.2 0 0 1-4.2-1.2l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2Zm4.5-6.1c-.2-.1-1.5-.7-1.7-.8-.2-.1-.4-.1-.6.1l-.8 1c-.1.2-.3.2-.5.1a6.7 6.7 0 0 1-3.3-2.9c-.3-.4.3-.4.7-1.3.1-.2 0-.3 0-.4l-.8-1.8c-.2-.5-.4-.4-.6-.4h-.5a1 1 0 0 0-.7.3 3 3 0 0 0-.9 2.2 5.2 5.2 0 0 0 1.1 2.7 11.8 11.8 0 0 0 4.5 4c1.7.7 2.3.8 3.2.6.5-.1 1.5-.6 1.7-1.2.2-.6.2-1.1.2-1.2-.1-.1-.3-.2-.5-.3Z"
        />
      </svg>
      {children}
    </a>
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

function NumeroQueConta({ n, i }: { n: NumeroMercado; i: number }) {
  const [ref, visivel] = useVisivel<HTMLLIElement>()
  const c = CONTAGEM_MERCADO[n.valor]
  const valor = useContador(c?.numero ?? 0, visivel, 1500)
  const exibido = c ? `${c.antes ?? ''}${valor.toLocaleString('pt-BR', { minimumFractionDigits: c.casas, maximumFractionDigits: c.casas })}${c.depois}` : n.valor
  return (
    <li ref={ref} className="lp-numero-mercado" data-reveal style={atraso(i)}>
      <span className="lp-numero-valor">
        <span aria-hidden="true">{exibido}</span>
        <span className="lp-so-leitor">{n.valor}</span>
      </span>
      <p>{n.texto}</p>
      <Fonte id={n.fonte} />
    </li>
  )
}

function Titulo() {
  const i = useGiro(PRATOS_GIRO.length, 2400)
  return (
    <h1 className="lp-titulo" aria-label="Quanto sobra de cada prato depois da taxa do app?">
      <span aria-hidden="true">
        Quanto sobra{' '}
        <span className="lp-giro">
          {PRATOS_GIRO.map((p, j) => (
            <span key={p} className={j === i ? 'ativo' : ''}>
              {p}
            </span>
          ))}
        </span>{' '}
        depois da taxa do app?
      </span>
    </h1>
  )
}

function Faixa() {
  const itens = (copia: boolean) =>
    RECURSOS_FAIXA.map((r) => (
      <li key={r.texto + copia} aria-hidden={copia || undefined}>
        {r.texto}
        {r.breve && <span className="lp-faixa-breve">em breve</span>}
      </li>
    ))
  return (
    <div className="lp-faixa" aria-label="O que o LucraFood faz">
      <ul className="lp-faixa-trilho">
        {itens(false)}
        {itens(true)}
      </ul>
    </div>
  )
}

function Fechamento() {
  return (
    <div className="lp-fechamento-demo">
      <div>
        <h3>Quer ver isso com o seu cardápio?</h3>
        <p>No piloto gratuito, você manda a foto e a gente monta o painel do seu restaurante junto com você.</p>
      </div>
      <BotaoPiloto>Quero com o meu cardápio</BotaoPiloto>
    </div>
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
            <img src={logoBranco} alt="LucraFood" height={28} />
          </a>
          <nav aria-label="Seções">
            <a href="#como-funciona">Como funciona</a>
            <a href="#demo">Demo</a>
            <a href="#perguntas">Perguntas</a>
            <a className="lp-nav-cta" href="#piloto">Piloto gratuito</a>
          </nav>
        </div>
      </header>

      <main id="conteudo">
        {/* 1. Topo */}
        <section id="topo" className="lp-topo">
          <div className="lp-topo-fundo" aria-hidden="true">
            <span className="lp-mancha lp-mancha-1" />
            <span className="lp-mancha lp-mancha-2" />
            <span className="lp-mancha lp-mancha-3" />
          </div>
          <div className="lp-conteudo lp-topo-grade">
            <div className="lp-topo-texto">
              <p className="lp-selo-topo">
                <span className="lp-ponto-vivo" aria-hidden="true" /> Para restaurantes que vendem por app de delivery
              </p>
              <Titulo />
              <p className="lp-subtitulo">
                Tire uma foto do cardápio. O LucraFood lê os pratos com IA, você confere, e ele mostra prato a prato quanto fica
                para você depois de ingredientes, imposto e taxa do app.
              </p>
              <div className="lp-acoes">
                <BotaoPiloto />
                <a className="botao lp-botao-vidro" href="#demo">Testar a demo agora</a>
              </div>
              <p className="lp-topo-nota">Grátis durante o piloto · a demo funciona sem cadastro</p>
            </div>
            <CenaTopo />
          </div>
        </section>

        {/* 2. Faixa */}
        <Faixa />

        {/* 3. O problema */}
        <section id="problema" className="lp-secao" aria-labelledby="problema-titulo">
          <div className="lp-conteudo">
            <p className="lp-sobretitulo" data-reveal>O problema</p>
            <h2 id="problema-titulo" data-reveal style={atraso(1)}>O delivery cresceu. A conta ficou mais difícil.</h2>
            <ul className="lp-grade-numeros">
              {NUMEROS_MERCADO.map((n, i) => (
                <NumeroQueConta key={n.valor} n={n} i={i} />
              ))}
            </ul>
            <p className="lp-fechamento" data-reveal>
              Muitos donos sabem o preço de venda. Poucos sabem quanto sobra depois de ingredientes, embalagem, imposto e taxa do
              app.
            </p>
          </div>
        </section>

        {/* 4. Como funciona */}
        <section id="como-funciona" className="lp-secao lp-secao-clara" aria-labelledby="como-titulo">
          <div className="lp-conteudo">
            <p className="lp-sobretitulo" data-reveal>Como funciona</p>
            <h2 id="como-titulo" data-reveal style={atraso(1)}>Três passos, e quem decide é você</h2>
            <ComoFunciona />
          </div>
        </section>

        {/* 5. A conta */}
        <section id="a-conta" className="lp-secao" aria-labelledby="conta-titulo">
          <div className="lp-conteudo lp-conta-grade">
            <div>
              <p className="lp-sobretitulo" data-reveal>A conta que ninguém te mostra</p>
              <h2 id="conta-titulo" data-reveal style={atraso(1)}>O cliente paga R$ 24,90. Quanto disso é seu?</h2>
              <p className="lp-texto-grande" data-reveal style={atraso(2)}>
                O app mostra o que você vendeu. O LucraFood mostra o que sobrou: cada pedido descontado linha por linha, com o seu
                custo, o seu imposto e a sua taxa.
              </p>
              <p className="suave pequeno" data-reveal style={atraso(3)}>
                Exemplo com o X-Burger da lanchonete fictícia da demo, taxa de 26% e imposto de 6%.
              </p>
            </div>
            <div data-reveal style={atraso(2)}>
              <Cupom />
            </div>
          </div>
        </section>

        {/* 6. Demo */}
        <section id="demo" className="lp-secao lp-secao-demo" aria-labelledby="demo-titulo">
          <div className="lp-conteudo">
            <div className="lp-demo-cabeca">
              <p className="lp-sobretitulo" data-reveal>Demo interativa</p>
              <h2 id="demo-titulo" data-reveal style={atraso(1)}>Faça você mesmo, em menos de 1 minuto</h2>
              <p data-reveal style={atraso(2)}>
                Uma lanchonete de exemplo. As respostas da IA foram gravadas de uma leitura real, então a demo não gasta nada e nada
                sai do seu navegador.
              </p>
            </div>
            <Suspense fallback={<p className="lp-carregando">Carregando a demo…</p>}>
              <Demo fechamento={<Fechamento />} />
            </Suspense>
          </div>
        </section>

        {/* 7. Sem × Com */}
        <section id="sem-com" className="lp-secao" aria-labelledby="semcom-titulo">
          <div className="lp-conteudo">
            <p className="lp-sobretitulo" data-reveal>O que muda</p>
            <h2 id="semcom-titulo" data-reveal style={atraso(1)}>Sem o LucraFood × com o LucraFood</h2>
            <div className="lp-sem-com">
              <div className="lp-coluna-sem" data-reveal style={atraso(1)}>
                <h3>Sem</h3>
                <ul>{SEM_COM.sem.map((t) => <li key={t}>{t}</li>)}</ul>
              </div>
              <div className="lp-coluna-com" data-reveal style={atraso(2)}>
                <h3>Com o LucraFood</h3>
                <ul>{SEM_COM.com.map((t) => <li key={t}>{t}</li>)}</ul>
              </div>
            </div>

            <h3 className="lp-subsecao" data-reveal>O que o LucraFood já faz hoje</h3>
            <ul className="lp-lista-beneficios">
              {[
                ['Ver quais pratos dão pouco lucro no delivery.', 'O painel separa os pratos em saudável, atenção e crítico pela margem depois da taxa do app.'],
                ['Ver a conta inteira, linha por linha:', 'preço − ingredientes − embalagem − imposto − taxa do app = o que sobra.'],
                ['Saber o custo de cada ingrediente da receita,', 'inclusive de receitas que rendem várias porções.'],
                ['Um preço sugerido', 'para chegar na margem que você escolheu, sempre marcado como sugestão.'],
              ].map(([forte, resto], i) => (
                <li key={forte} data-reveal style={atraso(i)}>
                  <strong>{forte}</strong> {resto}
                </li>
              ))}
            </ul>

            <h3 className="lp-subsecao" data-reveal>O que vem por aí</h3>
            <ul className="lp-grade-breve">
              {[
                ['Testar um preço novo', 'Mude o preço e veja a sobra e o farol mudarem antes de mexer no app de delivery.'],
                ['Ingrediente ficou mais caro', 'A carne subiu? Veja quais pratos foram afetados e quanto a sobra de cada um caiu.'],
                ['Preço de ingrediente antigo', 'Aviso quando um preço está há mais de 30 dias sem atualizar: a conta pode estar desatualizada.'],
              ].map(([titulo, texto], i) => (
                <li key={titulo} className="cartao" data-reveal style={atraso(i)}>
                  <Etiqueta origem="Funciona na demo; ainda não está no app real.">Em desenvolvimento</Etiqueta>
                  <h3>{titulo}</h3>
                  <p>{texto}</p>
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* 8. Confiança + perguntas */}
        <section id="perguntas" className="lp-secao lp-secao-clara" aria-labelledby="perguntas-titulo">
          <div className="lp-conteudo lp-perguntas-grade">
            <div>
              <p className="lp-sobretitulo" data-reveal>Por que confiar</p>
              <h2 data-reveal style={atraso(1)}>A IA ajuda. Quem faz a conta é o sistema.</h2>
              <ul className="lp-confianca">
                {[
                  ['A IA lê, você confere, o sistema calcula.', 'A IA nunca faz conta.'],
                  ['Estimativa vem marcada como estimativa.', 'Sugestão de preço também.'],
                  ['O sistema avisa o que ainda não sabe,', 'como prato sem receita ou sem preço, em vez de mostrar um número bonito e errado.'],
                ].map(([forte, resto], i) => (
                  <li key={forte} data-reveal style={atraso(i + 2)}>
                    <strong>{forte}</strong> {resto}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h2 id="perguntas-titulo" data-reveal>Perguntas frequentes</h2>
              <div className="lp-faq">
                {PERGUNTAS.map((p, i) => (
                  <details key={p.pergunta} data-reveal style={atraso(i)}>
                    <summary>{p.pergunta}</summary>
                    <p>{p.resposta}</p>
                  </details>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* 9. Oferta */}
        <section id="piloto" className="lp-piloto" aria-labelledby="piloto-titulo">
          <div className="lp-topo-fundo" aria-hidden="true">
            <span className="lp-mancha lp-mancha-1" />
            <span className="lp-mancha lp-mancha-2" />
          </div>
          <div className="lp-conteudo lp-piloto-conteudo" data-reveal>
            <p className="lp-selo-topo">Piloto gratuito</p>
            <h2 id="piloto-titulo">Descubra quanto sobra de cada prato do seu cardápio</h2>
            <p>
              Me chame no WhatsApp e mande a foto do cardápio. A gente monta o painel do seu restaurante junto, de graça, enquanto o
              LucraFood está em piloto. Ainda não há plano pago.
            </p>
            <div className="lp-acoes">
              <BotaoPiloto />
              <a className="botao lp-botao-vidro" href={CONTATO_EMAIL}>Prefiro e-mail</a>
            </div>
          </div>
        </section>
      </main>

      {/* 10. Rodapé */}
      <footer className="lp-rodape">
        <div className="lp-conteudo">
          <div className="lp-rodape-topo">
            <div>
              <img src={logoBranco} alt="LucraFood" height={28} />
              <p>Quanto sobra de cada prato no delivery.</p>
            </div>
            <nav aria-label="Rodapé" className="lp-rodape-links">
              <a href="#como-funciona">Como funciona</a>
              <a href="#demo">Demo</a>
              <a href="#perguntas">Perguntas</a>
              <Link to="/por-dentro">Por dentro (para desenvolvedores)</Link>
              <a href={REPOSITORIO} target="_blank" rel="noopener noreferrer">GitHub</a>
            </nav>
          </div>
          <details className="lp-rodape-fontes">
            <summary>Fontes dos números</summary>
            <ol>
              {FONTES.map((f) => (
                <li key={f.id}>
                  <a href={f.url} target="_blank" rel="noopener noreferrer">{f.titulo}</a> — {f.quem}.
                </li>
              ))}
            </ol>
          </details>
          <p className="lp-rodape-autor">
            © 2026 LucraFood · Criado por{' '}
            <a href={LINKEDIN} target="_blank" rel="noopener noreferrer">{AUTOR}</a>
          </p>
        </div>
      </footer>
    </div>
  )
}
