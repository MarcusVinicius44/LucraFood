// Regra do produto: só mostrar como fato o que dá para provar.
// Tudo que é estimativa ou sugestão leva esta etiqueta e diz de onde veio (no title e no texto ao lado).
export function Etiqueta({ children, origem }: { children: React.ReactNode; origem: string }) {
  return (
    <span className="etiqueta" title={origem}>
      {children}
    </span>
  )
}
