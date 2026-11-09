// Prepara a foto para o backend (JPG/PNG/WEBP até 4 MB).
// Foto que já cabe vai como está, igual às fotos da avaliação (evals/cardapios).
// Só a que passa do limite (comum em celular) é reduzida aqui.

export const TIPOS_ACEITOS = ['image/jpeg', 'image/png', 'image/webp']
export const TAMANHO_MAX = 4 * 1024 * 1024
const LADO_MAX = 2400 // px no lado maior: ainda dá para ler letra pequena de cardápio
const QUALIDADE = 0.92 // medido em 09/11: 0,85 e 0,92 erram dígitos manuscritos em foto pequena (README, "Foto reduzida pelo navegador")

export interface FotoPronta {
  arquivo: Blob
  nome: string
  reduzida: boolean
}

/** HEIC/HEIF: formato de "alta eficiência" de iPhone e de alguns Android (opção no app da câmera). */
export function ehHeic(arquivo: { type: string; name: string }): boolean {
  return /image\/hei[cf]/i.test(arquivo.type) || /\.hei[cf]$/i.test(arquivo.name)
}

export const MSG_HEIC =
  'Esta foto está em HEIC (alta eficiência) e o navegador não conseguiu abrir. ' +
  'Na câmera do celular, desligue "Fotos de alta eficiência" (Samsung) ou escolha "Mais compatível" (iPhone) e tire de novo.'

export async function prepararFoto(arquivo: File): Promise<FotoPronta> {
  if (TIPOS_ACEITOS.includes(arquivo.type) && arquivo.size <= TAMANHO_MAX) {
    return { arquivo, nome: arquivo.name, reduzida: false }
  }
  if (!arquivo.type.startsWith('image/') && !ehHeic(arquivo)) {
    throw new Error('Este arquivo não é uma imagem. Envie uma foto em JPG, PNG ou WEBP.')
  }
  // HEIC e fotos grandes passam pelo canvas e saem em JPEG. Alguns navegadores (Safari) abrem HEIC;
  // o Chrome em geral não, e aí a mensagem explica como mudar a câmera.
  let bitmap: ImageBitmap
  try {
    bitmap = await createImageBitmap(arquivo) // respeita a orientação (EXIF) da foto
  } catch {
    throw new Error(ehHeic(arquivo) ? MSG_HEIC : 'Não consegui abrir essa imagem. Envie uma foto em JPG, PNG ou WEBP.')
  }
  try {
    const escala = Math.min(1, LADO_MAX / Math.max(bitmap.width, bitmap.height))
    const canvas = document.createElement('canvas')
    canvas.width = Math.round(bitmap.width * escala)
    canvas.height = Math.round(bitmap.height * escala)
    const ctx = canvas.getContext('2d')
    if (!ctx) throw new Error('sem canvas')
    ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height)
    const blob = await new Promise<Blob | null>((ok) => canvas.toBlob(ok, 'image/jpeg', QUALIDADE))
    if (!blob) throw new Error('sem blob')
    if (blob.size > TAMANHO_MAX) throw new Error('A foto ficou grande demais mesmo reduzida. Tente outra foto.')
    const nome = arquivo.name.replace(/\.[^.]+$/, '') + '.jpg'
    return { arquivo: blob, nome, reduzida: true }
  } catch (erro) {
    const msg = (erro as Error).message
    // Falha de memória no celular costuma aparecer aqui, com foto de muitos megapixels.
    throw new Error(msg.startsWith('A foto') ? msg : 'Não consegui preparar a foto (o celular pode estar sem memória). Feche outros apps ou escolha a foto pela galeria.')
  } finally {
    bitmap.close()
  }
}
