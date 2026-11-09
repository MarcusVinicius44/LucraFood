import { describe, expect, it } from 'vitest'
import { ehHeic } from './imagem'

describe('ehHeic', () => {
  it('reconhece pelo tipo ou pela extensão', () => {
    expect(ehHeic({ type: 'image/heic', name: 'a.jpg' })).toBe(true)
    expect(ehHeic({ type: 'image/heif', name: 'a' })).toBe(true)
    expect(ehHeic({ type: '', name: 'IMG_0001.HEIC' })).toBe(true) // Chrome às vezes manda tipo vazio
    expect(ehHeic({ type: 'image/jpeg', name: 'foto.jpg' })).toBe(false)
  })
})
