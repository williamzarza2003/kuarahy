import { useEffect, useRef, useState } from 'react'
import type { Configuracion } from '../data/configuracion.ts'
import { aURL, varianteDe } from '../data/configuracion.ts'
import { dibujarGrabado, fuenteLista } from '../lib/grabado.ts'

// Lo mínimo de la API de <model-viewer> que usamos
interface MaterialMV {
  name: string
  setAlphaMode(modo: 'OPAQUE' | 'MASK' | 'BLEND'): void
  pbrMetallicRoughness: {
    setBaseColorFactor(c: string | number[]): void
    setMetallicFactor(v: number): void
    setRoughnessFactor(v: number): void
    baseColorTexture: { setTexture(t: unknown): void }
  }
}
interface ModelViewer extends HTMLElement {
  canActivateAR: boolean
  loaded: boolean
  updateComplete: Promise<boolean>
  model?: { materials: MaterialMV[] }
  createTexture(uri: string): Promise<unknown>
  activateAR(): void
}

declare module 'react' {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace JSX {
    interface IntrinsicElements {
      'model-viewer': React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & Record<string, unknown>
    }
  }
}

/**
 * <model-viewer> elige el modo de AR (WebXR, Scene Viewer o Quick Look) en su primer ciclo de
 * actualización, después de que se define el elemento, y en Android y en Chrome de escritorio
 * todavía espera a `navigator.xr.isSessionSupported`. Leer `canActivateAR` apenas se define da
 * `false` en cualquier celular: por eso el iPhone mostraba el QR de "desde la computadora".
 * Primero esperamos la actualización (alcanza para Quick Look) y, si todavía dice que no, la carga
 * del modelo, que siempre llega después de esa consulta.
 */
async function puedeUsarAR(mv: ModelViewer): Promise<boolean> {
  await customElements.whenDefined('model-viewer')
  await mv.updateComplete
  if (mv.canActivateAR) return true
  if (!mv.loaded) {
    await new Promise<void>((listo) => {
      const fin = () => {
        mv.removeEventListener('load', fin)
        mv.removeEventListener('error', fin)
        listo()
      }
      mv.addEventListener('load', fin)
      mv.addEventListener('error', fin)
    })
  }
  return mv.canActivateAR
}

/**
 * "Ver en tu mesa": realidad aumentada con <model-viewer>, que se baja recién al abrir.
 * - Android: WebXR en Chrome (respeta el color y el nombre); si no hay, Scene Viewer.
 * - iPhone: Quick Look, con un USDZ que model-viewer arma en el momento desde la escena personalizada.
 * - Computadora: no hay AR, así que mostramos un QR para seguir en el celular con el mismo diseño.
 */
export default function VerEnMesa({ config, abierto, onCerrar }: { config: Configuracion; abierto: boolean; onCerrar: () => void }) {
  const dialogo = useRef<HTMLDialogElement>(null)
  const visor = useRef<ModelViewer>(null)
  const [listo, setListo] = useState(false)
  const [puedeAR, setPuedeAR] = useState<boolean | null>(null)
  const [qr, setQr] = useState('')
  const enlace = `${location.origin}${location.pathname}${aURL(config)}#hacelo`

  useEffect(() => {
    const d = dialogo.current
    if (!d) return
    if (abierto && !d.open) {
      d.showModal()
      import('@google/model-viewer').then(() => setListo(true))
    } else if (!abierto && d.open) d.close()
  }, [abierto])

  // ¿Este dispositivo puede abrir la realidad aumentada?
  useEffect(() => {
    const mv = visor.current
    if (!listo || !mv) return
    let vigente = true
    puedeUsarAR(mv).then((si) => vigente && setPuedeAR(si))
    return () => {
      vigente = false
    }
  }, [listo])

  // Al cargar el modelo: color y nombre como en el visor (y en el USDZ que arma model-viewer para el iPhone)
  useEffect(() => {
    const mv = visor.current
    if (!listo || !mv) return
    const aplicar = async () => {
      const mats = mv.model?.materials ?? []
      mats.find((m) => m.name === 'Pintura')?.pbrMetallicRoughness.setBaseColorFactor(varianteDe(config.color).base)
      const nombre = mats.find((m) => m.name === 'Nombre')
      if (nombre) {
        // <model-viewer> no toma el alfa de una textura creada en vivo: la banda va opaca, del color del termo
        await fuenteLista()
        const canvas = document.createElement('canvas')
        dibujarGrabado(canvas, config.nombre, varianteDe(config.color).base)
        nombre.setAlphaMode('OPAQUE')
        nombre.pbrMetallicRoughness.setBaseColorFactor('#ffffff')
        nombre.pbrMetallicRoughness.setMetallicFactor(0)
        nombre.pbrMetallicRoughness.setRoughnessFactor(0.5)
        nombre.pbrMetallicRoughness.baseColorTexture.setTexture(await mv.createTexture(canvas.toDataURL('image/png')))
      }
    }
    mv.addEventListener('load', aplicar)
    return () => mv.removeEventListener('load', aplicar)
  }, [listo, config])

  // QR solo si no se puede abrir la realidad aumentada en este dispositivo
  useEffect(() => {
    if (puedeAR !== false) return
    import('qrcode').then((q) => q.toDataURL(enlace, { margin: 1, width: 220, color: { dark: '#11161a', light: '#ffffff' } })).then(setQr)
  }, [puedeAR, enlace])

  const tam = config.tamano
  return (
    <dialog ref={dialogo} className="mesa" onClose={onCerrar} aria-labelledby="titulo-mesa">
      <div className="mesa__cabecera">
        <h2 id="titulo-mesa">Ver en tu mesa</h2>
        <button type="button" className="mesa__cerrar" onClick={onCerrar}>Cerrar</button>
      </div>
      {listo ? (
        <model-viewer
          ref={visor}
          className="mesa__visor"
          src={`/modelos/kuarahy-${tam}-${config.tapa}.glb`}
          alt={`Termo Kuarahy ${varianteDe(config.color).nombre}, ${tam === '15L' ? '1,5 L' : '1 L'}, en realidad aumentada`}
          // React 19 pasa a propiedad todo lo que el elemento define como propiedad: ar="" quedaba
          // como mv.ar = "" (falso) y model-viewer nunca activaba la AR. Tiene que ir como booleano.
          ar={true}
          ar-modes="webxr scene-viewer quick-look"
          ar-scale="fixed"
          camera-controls=""
          touch-action="pan-y"
          shadow-intensity="1"
          environment-image="neutral"
          exposure="1.05"
          camera-orbit="-20deg 78deg auto"
        >
          <button slot="ar-button" className="boton mesa__ar">Ponerlo sobre la mesa</button>
        </model-viewer>
      ) : (
        <p className="mesa__cargando" role="status">Preparando el termo en 3D…</p>
      )}
      {puedeAR === false && (
        <div className="mesa__qr">
          {qr && <img src={qr} width={160} height={160} alt="Código QR con este mismo diseño" />}
          <p>
            Desde la computadora no se puede usar la cámara. <strong>Escaneá el código con el celular</strong>: se abre
            este mismo diseño y lo ponés en tu mesa a tamaño real.
          </p>
        </div>
      )}
      {puedeAR && <p className="mesa__nota">Apuntá la cámara a una mesa y movela despacio hasta que aparezca el termo, a tamaño real.</p>}
    </dialog>
  )
}
