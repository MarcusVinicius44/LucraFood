import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ErroApi, extrairCardapio } from '../api'
import { salvarRascunho } from '../armazenamento'
import logoBranco from '../assets/lucrafood-logo-branco.svg'
import { Carregando } from '../componentes/Carregando'
import { type FotoPronta, prepararFoto } from '../imagem'

type Falha = { mensagem: string; motivo?: string; trocarFoto: boolean }

// Marca "a câmera foi aberta". Se a página carregar de novo com a marca ainda lá, o celular
// fechou a aba enquanto a câmera estava aberta (comum no Android com pouca memória).
const MARCA_CAMERA = 'lucrafood.camera_aberta'
const marcarCamera = (aberta: boolean) => {
  try {
    if (aberta) sessionStorage.setItem(MARCA_CAMERA, '1')
    else sessionStorage.removeItem(MARCA_CAMERA)
  } catch {
    /* sem armazenamento: só não detecta */
  }
}
const cameraFicouAberta = () => {
  try {
    return sessionStorage.getItem(MARCA_CAMERA) === '1'
  } catch {
    return false
  }
}

const MSG_PAGINA_RECARREGADA =
  'O celular fechou esta página enquanto a câmera estava aberta, e a foto se perdeu. ' +
  'Tente de novo; se repetir, tire a foto pelo app da câmera e use "Escolher da galeria".'

export function TelaFoto() {
  const navegar = useNavigate()
  const camera = useRef<HTMLInputElement>(null)
  const galeria = useRef<HTMLInputElement>(null)
  const [foto, setFoto] = useState<FotoPronta | null>(null)
  const [previa, setPrevia] = useState<string | null>(null)
  const [preparando, setPreparando] = useState(false)
  const [lendo, setLendo] = useState(false)
  const [falha, setFalha] = useState<Falha | null>(() =>
    cameraFicouAberta() ? { mensagem: MSG_PAGINA_RECARREGADA, trocarFoto: true } : null,
  )

  useEffect(() => {
    marcarCamera(false)
    // Voltou da câmera com a página viva (foto tirada ou cancelada): não houve recarga.
    const aoVoltar = () => { if (document.visibilityState === 'visible') marcarCamera(false) }
    document.addEventListener('visibilitychange', aoVoltar)
    return () => document.removeEventListener('visibilitychange', aoVoltar)
  }, [])

  // Libera da memória a prévia anterior quando troca de foto.
  useEffect(() => () => { if (previa) URL.revokeObjectURL(previa) }, [previa])

  function abrirCamera() {
    marcarCamera(true)
    camera.current?.click()
  }

  async function escolher(evento: React.ChangeEvent<HTMLInputElement>) {
    marcarCamera(false)
    const arquivo = evento.target.files?.[0]
    evento.target.value = '' // permite escolher a mesma foto de novo
    if (!arquivo) return
    setFalha(null)
    setFoto(null)
    setPrevia(null)
    setPreparando(true)
    try {
      const pronta = await prepararFoto(arquivo)
      setFoto(pronta)
      setPrevia(URL.createObjectURL(pronta.arquivo))
    } catch (erro) {
      setFalha({ mensagem: (erro as Error).message, trocarFoto: true })
    } finally {
      setPreparando(false)
    }
  }

  async function ler() {
    if (!foto || lendo) return
    setLendo(true)
    setFalha(null)
    try {
      const cardapio = await extrairCardapio(foto.arquivo, foto.nome)
      salvarRascunho(cardapio.pratos)
      navegar('/app/revisao')
    } catch (erro) {
      const e = erro instanceof ErroApi ? erro : new ErroApi(0, 'Erro inesperado ao ler a foto.')
      setFalha({
        mensagem: e.message,
        motivo: e.codigo === 'foto_ilegivel' && typeof e.dados.motivo === 'string' ? e.dados.motivo : undefined,
        // 422 e 400 são problema da foto; 429/503/502/rede valem tentar de novo com a mesma foto.
        trocarFoto: e.status === 422 || e.status === 400,
      })
    } finally {
      setLendo(false)
    }
  }

  function trocarFoto() {
    setFoto(null)
    setPrevia(null)
    setFalha(null)
    abrirCamera()
  }

  return (
    <div className="pilha">
      <section className="hero">
        <img src={logoBranco} alt="LucraFood" />
        <h1>Fotografe seu cardápio</h1>
        <p>A IA lê os pratos e os preços. Você confere tudo antes de salvar, e as contas de custo e margem são feitas pelo sistema, não pela IA.</p>
      </section>

      <input ref={camera} className="escondido" type="file" accept="image/*" capture="environment" onChange={escolher} />
      <input ref={galeria} className="escondido" type="file" accept="image/jpeg,image/png,image/webp" onChange={escolher} />

      <section className="cartao pilha">
        {preparando ? (
          <Carregando titulo="Preparando a foto…" detalhe="Fotos grandes do celular são reduzidas antes do envio." />
        ) : lendo ? (
          <Carregando titulo="Lendo o cardápio…" detalhe="Costuma levar de 10 a 40 segundos. Se a IA estiver sobrecarregada, pode passar de 1 minuto." />
        ) : (
          <>
            {previa ? (
              <img className="previa" src={previa} alt="Foto do cardápio escolhida" />
            ) : (
              <p className="suave">Dica: boa luz, celular parado e o cardápio inteiro aparecendo na foto.</p>
            )}
            {foto?.reduzida && (
              <p className="suave pequeno">A foto passava de 4 MB e foi reduzida antes do envio.</p>
            )}

            {falha && (
              <div className="aviso aviso-erro" role="alert">
                <p>{falha.mensagem}</p>
                {falha.motivo && <p className="pequeno">Motivo informado pela IA: {falha.motivo}</p>}
              </div>
            )}

            {foto && !falha?.trocarFoto ? (
              <>
                <button className="botao botao-primario botao-largo" onClick={ler}>
                  {falha ? 'Tentar de novo' : 'Ler cardápio'}
                </button>
                <button className="botao botao-texto" onClick={trocarFoto}>
                  Trocar foto
                </button>
              </>
            ) : (
              <div className="pilha">
                <button className="botao botao-primario botao-largo" onClick={falha?.trocarFoto ? trocarFoto : abrirCamera}>
                  {falha?.trocarFoto ? 'Tirar outra foto' : 'Tirar foto'}
                </button>
                <button className="botao botao-secundario botao-largo" onClick={() => galeria.current?.click()}>
                  Escolher da galeria
                </button>
              </div>
            )}
          </>
        )}
      </section>
    </div>
  )
}
