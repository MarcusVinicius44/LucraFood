import { Link, NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { restauranteSalvo } from './armazenamento'
import logo from './assets/lucrafood-logo.svg'
import simbolo from './assets/lucrafood-simbolo.svg'
import { TelaAjustes } from './telas/TelaAjustes'
import { TelaFoto } from './telas/TelaFoto'
import { TelaIngredientes } from './telas/TelaIngredientes'
import { TelaPainel } from './telas/TelaPainel'
import { TelaPrato } from './telas/TelaPrato'
import { TelaRevisao } from './telas/TelaRevisao'

function Inicio() {
  // Quem já tem restaurante cai direto no painel; quem chega pela primeira vez, na foto.
  return <Navigate to={restauranteSalvo() ? '/app/painel' : '/app/foto'} replace />
}

/** O app real, sob /app (as rotas abaixo são relativas a /app). */
export default function App() {
  return (
    <>
      <header className="cabecalho">
        <div className="cabecalho-conteudo">
          <Link to="/app" aria-label="LucraFood, início do app">
            {/* Logo inteiro na tela larga; só o símbolo no celular, para caber a navegação. */}
            <img className="logo-largo" src={logo} alt="LucraFood" />
            <img className="logo-curto" src={simbolo} alt="LucraFood" />
          </Link>
          <nav>
            <NavLink to="/app/painel">Painel</NavLink>
            <NavLink to="/app/ingredientes">Ingredientes</NavLink>
            <NavLink to="/app/ajustes">Ajustes</NavLink>
          </nav>
        </div>
      </header>
      <main className="pagina">
        <Routes>
          <Route index element={<Inicio />} />
          <Route path="foto" element={<TelaFoto />} />
          <Route path="revisao" element={<TelaRevisao />} />
          <Route path="painel" element={<TelaPainel />} />
          <Route path="pratos/:id" element={<TelaPrato />} />
          <Route path="ingredientes" element={<TelaIngredientes />} />
          <Route path="ajustes" element={<TelaAjustes />} />
          <Route path="*" element={<Inicio />} />
        </Routes>
      </main>
    </>
  )
}
