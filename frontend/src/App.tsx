import { Link, NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { restauranteSalvo } from './armazenamento'
import logo from './assets/lucrafood-logo.svg'
import { TelaFoto } from './telas/TelaFoto'
import { TelaPainel } from './telas/TelaPainel'
import { TelaRevisao } from './telas/TelaRevisao'

function Inicio() {
  // Quem já tem restaurante cai direto no painel; quem chega pela primeira vez, na foto.
  return <Navigate to={restauranteSalvo() ? '/painel' : '/foto'} replace />
}

export default function App() {
  return (
    <>
      <header className="cabecalho">
        <div className="cabecalho-conteudo">
          <Link to="/" aria-label="LucraFood, início">
            <img src={logo} alt="LucraFood" />
          </Link>
          <nav>
            <NavLink to="/foto">Foto</NavLink>
            <NavLink to="/painel">Painel</NavLink>
          </nav>
        </div>
      </header>
      <main className="pagina">
        <Routes>
          <Route path="/" element={<Inicio />} />
          <Route path="/foto" element={<TelaFoto />} />
          <Route path="/revisao" element={<TelaRevisao />} />
          <Route path="/painel" element={<TelaPainel />} />
          <Route path="*" element={<Inicio />} />
        </Routes>
      </main>
    </>
  )
}
