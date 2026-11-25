import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import { variantes } from '../data/variantes.ts'
import {
  fraseTapa, guaranies, limpiarNombre, MAX_NOMBRE, PRECIO_GRABADO, precio, tamanos, tapas, varianteDe, aURL,
  type Configuracion,
} from '../data/configuracion.ts'
import Render from './Render.tsx'

const Visor3D = lazy(() => import('./Visor3D.tsx'))
const VerEnMesa = lazy(() => import('./VerEnMesa.tsx'))

/** Conexión lenta, ahorro de datos o poca memoria: el 3D queda a un toque, no se baja solo. */
function dispositivoLiviano() {
  const nav = navigator as Navigator & { connection?: { saveData?: boolean; effectiveType?: string }; deviceMemory?: number }
  const red = nav.connection
  return Boolean(red?.saveData || /(^|-)2g|3g/.test(red?.effectiveType ?? '') || (nav.deviceMemory && nav.deviceMemory < 4))
}

interface Props {
  config: Configuracion
  setConfig: (c: Configuracion) => void
}

export default function Personalizador({ config, setConfig }: Props) {
  const seccion = useRef<HTMLElement>(null)
  const [cargar3D, setCargar3D] = useState(false)
  const [listo3D, setListo3D] = useState(false)
  const [manual] = useState(() =>
    dispositivoLiviano() || window.matchMedia('(prefers-reduced-motion: reduce)').matches)
  const [giro, setGiro] = useState({ grados: 0, n: 0 })
  const [mesa, setMesa] = useState(false)
  const [copiado, setCopiado] = useState(false)
  const variante = varianteDe(config.color)
  const cambiar = (parcial: Partial<Configuracion>) => setConfig({ ...config, ...parcial })

  // El 3D se baja cuando la sección está por aparecer (nunca bloquea la carga de la portada)
  useEffect(() => {
    if (manual || cargar3D) return
    const el = seccion.current
    if (!el) return
    const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) setCargar3D(true) }, { rootMargin: '400px 0px' })
    obs.observe(el)
    return () => obs.disconnect()
  }, [manual, cargar3D])

  const copiar = async () => {
    const url = `${location.origin}${location.pathname}${aURL(config)}#hacelo`
    try {
      if (navigator.share && matchMedia('(pointer: coarse)').matches) await navigator.share({ title: 'Mi Kuarahy', url })
      else await navigator.clipboard.writeText(url)
      setCopiado(true)
      setTimeout(() => setCopiado(false), 2500)
    } catch {
      // el usuario canceló compartir: no hace falta avisar nada
    }
  }

  const resumen = `${variante.nombre}, ${config.tamano === '15L' ? '1,5 L' : '1 L'}, ${fraseTapa(config.tapa)}${config.nombre.trim() ? `, con «${config.nombre.trim()}» grabado` : ''}`

  return (
    <section id="hacelo" ref={seccion} className="hacelo" aria-labelledby="titulo-hacelo">
      <div className="contenedor hacelo__grilla">
        <div className="visor3d" role="img" aria-label={`Vista del termo: ${resumen}`}>
          {/* Mientras carga (o en celulares lentos) se ve el render de Blender del mismo color */}
          <Render
            nombre={`estudio-${config.color}`}
            alt=""
            className={`visor3d__foto${listo3D ? ' visor3d__foto--oculta' : ''}`}
            sizes="(max-width: 900px) 92vw, 46vw"
            ancho={1200}
            alto={1500}
          />
          {cargar3D && (
            <Suspense fallback={null}>
              <Visor3D config={config} giro={giro} onListo={() => setListo3D(true)} />
            </Suspense>
          )}
          {!cargar3D && (
            <button type="button" className="boton boton--claro visor3d__activar" onClick={() => setCargar3D(true)}>
              Girarlo en 3D
            </button>
          )}
          {cargar3D && !listo3D && <p className="visor3d__estado" role="status">Cargando el termo en 3D…</p>}
          {listo3D && (
            <div className="visor3d__giro">
              <button type="button" onClick={() => setGiro({ grados: 45, n: giro.n + 1 })} aria-label="Girar el termo a la izquierda">⟲</button>
              <span aria-hidden="true">Arrastrá para girarlo</span>
              <button type="button" onClick={() => setGiro({ grados: -45, n: giro.n + 1 })} aria-label="Girar el termo a la derecha">⟳</button>
            </div>
          )}
        </div>

        <div className="hacelo__panel">
          <h2 id="titulo-hacelo">Hacé el tuyo</h2>
          <p className="hacelo__bajada">El mismo modelo de las fotos, en 3D: elegí cómo lo querés y miralo desde todos lados.</p>

          <fieldset className="opcion">
            <legend>Color <span className="opcion__valor">{variante.nombre}</span></legend>
            <div className="selector">
              {variantes.map((v) => (
                <label key={v.id} className={v.id === config.color ? 'swatch swatch--activo' : 'swatch'}>
                  <input type="radio" name="color" value={v.id} checked={v.id === config.color} onChange={() => cambiar({ color: v.id })} />
                  <span className="swatch__color" style={{ background: v.base }} aria-hidden="true" />
                  <span className="swatch__nombre">{v.nombre}</span>
                </label>
              ))}
            </div>
            <p className="opcion__nota" aria-live="polite">{variante.nota}</p>
          </fieldset>

          <div className="opcion">
            <label htmlFor="grabado" className="opcion__titulo">
              Grabado con tu nombre <span className="opcion__valor">+{guaranies(PRECIO_GRABADO)}</span>
            </label>
            <div className="grabado">
              <input
                id="grabado"
                value={config.nombre}
                onChange={(e) => cambiar({ nombre: limpiarNombre(e.target.value) })}
                maxLength={MAX_NOMBRE}
                autoComplete="off"
                spellCheck={false}
                placeholder="Ej.: Ña Rosa"
                aria-describedby="grabado-ayuda"
              />
              <span className="grabado__cuenta" aria-hidden="true">{config.nombre.length}/{MAX_NOMBRE}</span>
            </div>
            <p id="grabado-ayuda" className="opcion__nota">Se graba con láser debajo del logo. Hasta {MAX_NOMBRE} letras; acentos y ñ, sí.</p>
          </div>

          <fieldset className="opcion">
            <legend>Tapa</legend>
            <div className="tarjetas">
              {tapas.map((t) => (
                <label key={t.id} className={t.id === config.tapa ? 'tarjeta tarjeta--activa' : 'tarjeta'}>
                  <input type="radio" name="tapa" value={t.id} checked={t.id === config.tapa} onChange={() => cambiar({ tapa: t.id })} />
                  <strong>{t.nombre}</strong>
                  <span>{t.detalle}</span>
                  <span className="tarjeta__precio">{t.precio ? `+${guaranies(t.precio)}` : 'Incluida'}</span>
                </label>
              ))}
            </div>
          </fieldset>

          <fieldset className="opcion">
            <legend>Tamaño</legend>
            <div className="tarjetas">
              {tamanos.map((t) => (
                <label key={t.id} className={t.id === config.tamano ? 'tarjeta tarjeta--activa' : 'tarjeta'}>
                  <input type="radio" name="tamano" value={t.id} checked={t.id === config.tamano} onChange={() => cambiar({ tamano: t.id })} />
                  <strong>{t.nombre}</strong>
                  <span>{t.detalle}</span>
                  <span className="tarjeta__precio">{guaranies(t.precio)}</span>
                </label>
              ))}
            </div>
          </fieldset>

          <div className="hacelo__total">
            <p>
              <span className="hacelo__precio" aria-live="polite">{guaranies(precio(config))}</span>
              <span className="hacelo__resumen">{resumen}</span>
            </p>
            <div className="hacelo__acciones">
              <a href="#quiero" className="boton">Lo quiero así</a>
              <button type="button" className="boton boton--borde" onClick={() => setMesa(true)}>Ver en tu mesa</button>
              <button type="button" className="enlace" onClick={copiar} aria-live="polite">
                {copiado ? 'Enlace copiado' : 'Copiar el enlace de este diseño'}
              </button>
            </div>
          </div>
        </div>
      </div>
      {mesa && (
        <Suspense fallback={null}>
          <VerEnMesa config={config} abierto={mesa} onCerrar={() => setMesa(false)} />
        </Suspense>
      )}
    </section>
  )
}
