// Fluxo real do sistema, em SVG simples (sem biblioteca). Cada caixa é um pedaço do código.
const ETAPAS = [
  { titulo: 'Foto do cardápio', detalhe: 'JPG/PNG/WEBP até 4 MB', tipo: 'entrada' },
  { titulo: 'Gemini Flash-Lite', detalhe: 'visão, resposta em JSON', tipo: 'ia' },
  { titulo: 'Validação Pydantic', detalhe: '1 nova tentativa com o erro', tipo: 'codigo' },
  { titulo: 'Revisão humana', detalhe: 'o dono confere e corrige', tipo: 'humano' },
  { titulo: 'calculos.py', detalhe: 'Decimal, sem IA', tipo: 'codigo' },
  { titulo: 'Diagnóstico', detalhe: 'semáforo por prato', tipo: 'saida' },
] as const

export function Diagrama() {
  const largura = 220
  const altura = 64
  const passo = 92
  const total = ETAPAS.length * passo - (passo - altura)
  return (
    <svg
      className="lp-diagrama"
      viewBox={`0 0 ${largura + 40} ${total + 8}`}
      role="img"
      aria-labelledby="diagrama-titulo diagrama-desc"
    >
      <title id="diagrama-titulo">Fluxo do LucraFood</title>
      <desc id="diagrama-desc">
        Foto do cardápio, leitura pelo Gemini Flash-Lite, validação com Pydantic com uma nova tentativa, revisão humana,
        cálculo em calculos.py com Decimal e diagnóstico com semáforo.
      </desc>
      <defs>
        <marker id="seta" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="7" markerHeight="7" orient="auto">
          <path d="M0 0L10 5L0 10z" fill="currentColor" />
        </marker>
      </defs>
      {ETAPAS.map((e, i) => {
        const y = 4 + i * passo
        return (
          <g key={e.titulo}>
            <rect x={20} y={y} width={largura} height={altura} rx={12} className={`lp-dg-caixa lp-dg-${e.tipo}`} />
            <text x={20 + largura / 2} y={y + 27} textAnchor="middle" className="lp-dg-titulo">
              {e.titulo}
            </text>
            <text x={20 + largura / 2} y={y + 47} textAnchor="middle" className="lp-dg-detalhe">
              {e.detalhe}
            </text>
            {i < ETAPAS.length - 1 && (
              <line x1={20 + largura / 2} y1={y + altura + 2} x2={20 + largura / 2} y2={y + passo - 4} className="lp-dg-seta" markerEnd="url(#seta)" />
            )}
          </g>
        )
      })}
    </svg>
  )
}
