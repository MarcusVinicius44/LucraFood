import simbolo from '../assets/lucrafood-simbolo.svg'

export function Carregando({ titulo, detalhe }: { titulo: string; detalhe?: string }) {
  return (
    <div className="carregando" role="status" aria-live="polite">
      <img src={simbolo} alt="" />
      <strong>{titulo}</strong>
      {detalhe && <span className="suave pequeno">{detalhe}</span>}
    </div>
  )
}
