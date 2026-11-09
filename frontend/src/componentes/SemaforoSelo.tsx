import type { Semaforo } from '../api'

// Semáforo sempre com ícone + palavra: quem não distingue cor (ou imprime em P&B) entende igual.
const SELOS: Record<Semaforo | 'pendente', { rotulo: string; icone: React.ReactNode }> = {
  verde: {
    rotulo: 'Saudável',
    icone: <path d="M5 12.5l4.5 4.5L19 7.5" />,
  },
  amarelo: {
    rotulo: 'Atenção',
    icone: (
      <>
        <path d="M12 4l9 16H3z" />
        <path d="M12 10v4M12 17.5v.01" />
      </>
    ),
  },
  vermelho: {
    rotulo: 'Crítico',
    icone: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M9 9l6 6M15 9l-6 6" />
      </>
    ),
  },
  pendente: {
    rotulo: 'Sem dados',
    icone: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M8 12h8" />
      </>
    ),
  },
}

export function SemaforoSelo({ semaforo, rotulo }: { semaforo: Semaforo | null; rotulo?: string }) {
  const tipo = semaforo ?? 'pendente'
  const selo = SELOS[tipo]
  return (
    <span className={`semaforo semaforo-${tipo}`}>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        {selo.icone}
      </svg>
      {rotulo ?? selo.rotulo}
    </span>
  )
}
