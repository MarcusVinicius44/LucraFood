import { useEffect, useRef, useState } from 'react'

export const semMovimento = () =>
  typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

/** Marca [data-reveal] com .is-visible quando aparece na tela (a cascata vem de --d no CSS). */
export function useRevelar() {
  useEffect(() => {
    const alvos = Array.from(document.querySelectorAll('[data-reveal]'))
    if (!('IntersectionObserver' in window) || semMovimento()) {
      alvos.forEach((a) => a.classList.add('is-visible'))
      return
    }
    const obs = new IntersectionObserver(
      (entradas) =>
        entradas.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add('is-visible')
            obs.unobserve(e.target)
          }
        }),
      { rootMargin: '0px 0px -8% 0px' },
    )
    alvos.forEach((a) => obs.observe(a))
    return () => obs.disconnect()
  }, [])
}

/** true quando o elemento entra na tela (uma vez). */
export function useVisivel<T extends Element>(margem = '0px 0px -15% 0px') {
  const ref = useRef<T>(null)
  const [visivel, setVisivel] = useState(false)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    if (!('IntersectionObserver' in window)) {
      setVisivel(true)
      return
    }
    const obs = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          setVisivel(true)
          obs.disconnect()
        }
      },
      { rootMargin: margem },
    )
    obs.observe(el)
    return () => obs.disconnect()
  }, [margem])
  return [ref, visivel] as const
}

/** Conta de 0 até `fim` (com as casas de `fim`) quando `ativo` vira true. Só exibição. */
export function useContador(fim: number, ativo: boolean, duracaoMs = 1400) {
  const [valor, setValor] = useState(semMovimento() ? fim : 0)
  useEffect(() => {
    if (!ativo) return
    if (semMovimento()) {
      setValor(fim)
      return
    }
    let quadro = 0
    const inicio = performance.now()
    const passo = (agora: number) => {
      const t = Math.min(1, (agora - inicio) / duracaoMs)
      const suave = 1 - Math.pow(1 - t, 3)
      setValor(fim * suave)
      if (t < 1) quadro = requestAnimationFrame(passo)
    }
    quadro = requestAnimationFrame(passo)
    return () => cancelAnimationFrame(quadro)
  }, [fim, ativo, duracaoMs])
  return valor
}

/** Índice que avança a cada `intervaloMs` (parado para quem pede menos movimento). */
export function useGiro(total: number, intervaloMs = 2600) {
  const [i, setI] = useState(0)
  useEffect(() => {
    if (semMovimento() || total < 2) return
    const t = setInterval(() => setI((x) => (x + 1) % total), intervaloMs)
    return () => clearInterval(t)
  }, [total, intervaloMs])
  return i
}

/**
 * Fase de uma cena em loop: 0, 1, …, `fases - 1` a cada `passoMs`, segura a última por `pausaMs` e recomeça.
 * Só anda com `ativo` (cena na tela). Para quem pede menos movimento, fica parada na última fase.
 */
export function useLinhaDoTempo(fases: number, passoMs: number, pausaMs: number, ativo = true, repetir = true) {
  const [fase, setFase] = useState(() => (semMovimento() ? fases - 1 : 0))
  useEffect(() => {
    if (semMovimento() || !ativo) return
    const ultima = fase >= fases - 1
    if (ultima && !repetir) return
    const t = setTimeout(() => setFase(ultima ? 0 : fase + 1), ultima ? pausaMs : passoMs)
    return () => clearTimeout(t)
  }, [fase, fases, passoMs, pausaMs, ativo, repetir])
  return fase
}

/** Índice do item de `seletor` que está no meio da tela (para a seção contada pela rolagem). */
export function usePassoAtivo<T extends Element>(seletor: string) {
  const ref = useRef<T>(null)
  const [ativo, setAtivo] = useState(0)
  useEffect(() => {
    const raiz = ref.current
    if (!raiz || !('IntersectionObserver' in window)) return
    const itens = Array.from(raiz.querySelectorAll(seletor))
    const obs = new IntersectionObserver(
      (entradas) =>
        entradas.forEach((e) => {
          if (e.isIntersecting) setAtivo(itens.indexOf(e.target))
        }),
      { rootMargin: '-45% 0px -45% 0px' },
    )
    itens.forEach((i) => obs.observe(i))
    return () => obs.disconnect()
  }, [seletor])
  return [ref, ativo] as const
}

/** Valor que desliza do anterior até `alvo` (só exibição). */
export function useValorSuave(alvo: number, duracaoMs = 700) {
  const [valor, setValor] = useState(alvo)
  const atual = useRef(alvo)
  useEffect(() => {
    if (semMovimento()) {
      atual.current = alvo
      setValor(alvo)
      return
    }
    const de = atual.current
    let quadro = 0
    const inicio = performance.now()
    const passo = (agora: number) => {
      const t = Math.min(1, (agora - inicio) / duracaoMs)
      const v = de + (alvo - de) * (1 - Math.pow(1 - t, 3))
      atual.current = v
      setValor(v)
      if (t < 1) quadro = requestAnimationFrame(passo)
    }
    quadro = requestAnimationFrame(passo)
    return () => cancelAnimationFrame(quadro)
  }, [alvo, duracaoMs])
  return valor
}
