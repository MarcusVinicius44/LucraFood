// O que o navegador guarda. O MVP tem um restaurante só, sem login.
// Tudo com try/catch: em aba anônima ou com armazenamento bloqueado o app segue sem lembrar.

import type { PratoExtraido } from './api'

const CHAVE_RESTAURANTE = 'lucrafood.restaurante'
const CHAVE_RASCUNHO = 'lucrafood.rascunho'

export interface RestauranteSalvo {
  id: number
  nome: string
}

function ler<T>(armazem: () => Storage, chave: string): T | null {
  try {
    const texto = armazem().getItem(chave)
    return texto ? (JSON.parse(texto) as T) : null
  } catch {
    return null
  }
}

function gravar(armazem: () => Storage, chave: string, valor: unknown) {
  try {
    if (valor === null) armazem().removeItem(chave)
    else armazem().setItem(chave, JSON.stringify(valor))
  } catch {
    /* sem armazenamento: só não lembra */
  }
}

/** localStorage: o restaurante fica lembrado entre visitas. */
export const restauranteSalvo = () => ler<RestauranteSalvo>(() => localStorage, CHAVE_RESTAURANTE)
export const salvarRestaurante = (r: RestauranteSalvo) => gravar(() => localStorage, CHAVE_RESTAURANTE, r)
export const esquecerRestaurante = () => gravar(() => localStorage, CHAVE_RESTAURANTE, null)

/** sessionStorage: a leitura da IA sobrevive a um F5 na revisão, mas não fica para sempre. */
export const rascunho = () => ler<PratoExtraido[]>(() => sessionStorage, CHAVE_RASCUNHO)
export const salvarRascunho = (pratos: PratoExtraido[] | null) => gravar(() => sessionStorage, CHAVE_RASCUNHO, pratos)
