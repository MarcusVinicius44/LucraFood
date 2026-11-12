import { useEffect, useState } from 'react'
import { Carregando } from '../componentes/Carregando'
import { Etiqueta } from '../componentes/Etiqueta'
import { GRAVACAO } from './dadosDemo'
import foto from './fixtures/cardapio-sabor-da-esquina.png'

export const ORIGEM_GRAVACAO = `Resposta do ${GRAVACAO.modelo} gravada em ${GRAVACAO.data.split('-').reverse().join('/')} com esta foto; a demo não chama a IA.`

export function SeloGravado() {
  return <Etiqueta origem={ORIGEM_GRAVACAO}>Resultado gravado de uma leitura real feita pelo LucraFood com esta foto</Etiqueta>
}

export function DemoFoto({ atrasoMs, onLido }: { atrasoMs: number; onLido: () => void }) {
  const [lendo, setLendo] = useState(false)

  useEffect(() => {
    if (!lendo) return
    const t = setTimeout(onLido, atrasoMs)
    return () => clearTimeout(t)
  }, [lendo, atrasoMs, onLido])

  if (lendo) {
    return (
      <div className="pilha">
        <Carregando titulo="Lendo o cardápio…" detalhe="A IA procura nomes, categorias e preços." />
        <p className="demo-centro"><SeloGravado /></p>
      </div>
    )
  }
  return (
    <div className="demo-foto">
      <img
        src={foto}
        className="previa"
        alt="Cardápio da Lanchonete Sabor da Esquina (fictícia): lanches, porções e bebidas com preços de R$ 4,00 a R$ 34,90."
        width={540}
        height={720}
      />
      <div className="pilha">
        <h3>Esta é a foto do cardápio</h3>
        <p className="suave">
          No app, o dono tira a foto pelo celular. Aqui, a foto é de uma lanchonete inventada para a demo.
        </p>
        <button type="button" className="botao botao-primario" onClick={() => setLendo(true)}>
          Ler cardápio
        </button>
      </div>
    </div>
  )
}
