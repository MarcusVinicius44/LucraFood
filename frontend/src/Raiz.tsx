import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { Landing } from './landing/Landing'
import { PorDentro } from './landing/PorDentro'
import { REPOSITORIO } from './landing/conteudo'
import simbolo from './assets/lucrafood-simbolo.svg'

// "/" = landing com a demo (sem back-end). "/por-dentro" = a parte técnica. "/app" = o app real, que fala com o Django.
// O app só é baixado quando alguém abre /app, para a landing carregar leve.
const App = lazy(() => import('./App'))

/** Na versão publicada só com o front (Vercel), VITE_SEM_BACKEND=1 troca o app por este aviso. */
const SEM_BACKEND = import.meta.env.VITE_SEM_BACKEND === '1'

function AvisoSemBackend() {
  return (
    <main className="pagina">
      <div className="cartao pilha" style={{ marginTop: '3rem' }}>
        <img src={simbolo} alt="" width={48} height={48} />
        <h1>O app completo roda com o back-end</h1>
        <p className="suave">
          Esta versão publicada tem só a landing e a demo. O app de verdade (foto, revisão, painel, ficha técnica) precisa do
          servidor Django e de uma chave de IA. Veja como rodar no GitHub.
        </p>
        <div className="linha">
          <a className="botao botao-primario" href={`${REPOSITORIO}/blob/main/docs/DESENVOLVIMENTO.md`}>
            Como rodar no GitHub
          </a>
          <a className="botao botao-secundario" href="/#demo">
            Testar a demo
          </a>
        </div>
      </div>
    </main>
  )
}

export function Raiz() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/por-dentro" element={<PorDentro />} />
      <Route
        path="/app/*"
        element={
          SEM_BACKEND ? (
            <AvisoSemBackend />
          ) : (
            <Suspense fallback={<p className="pagina suave">Carregando o app…</p>}>
              <App />
            </Suspense>
          )
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
