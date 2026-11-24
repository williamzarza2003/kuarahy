import { useEffect, useRef, useState } from 'react'
import Render from './Render.tsx'
import type { Variante } from '../data/variantes.ts'

// Un día de enero en Ciudad del Este, contado por el termo
const capitulos = [
  { hora: 7, afuera: 29, adentro: 2, titulo: 'Siete de la mañana', texto: 'Llenás el termo con hielo hasta el cuello y le echás agua. Afuera ya hace calor.' },
  { hora: 11, afuera: 36, adentro: 2, titulo: 'Once', texto: 'La vereda quema. El primer termo de la oficina ya se quedó sin hielo.' },
  { hora: 15, afuera: 41, adentro: 3, titulo: 'Tres de la tarde', texto: 'La hora en que nadie sale. Adentro del Kuarahy, el hielo sigue entero.' },
  { hora: 20, afuera: 33, adentro: 4, titulo: 'Ocho de la noche', texto: 'Ronda de tereré en la vereda. El agua sale igual de fría que a la mañana.' },
  { hora: 31, afuera: 30, adentro: 6, titulo: 'Al otro día', texto: 'Veinticuatro horas después, todavía quedan cubitos. Ahí está la diferencia.' },
]

// Colores del cielo en cada capítulo (madrugada, mañana, siesta, noche, madrugada)
const cielos = [
  [255, 196, 140], [255, 160, 82], [255, 104, 36], [28, 36, 64], [255, 186, 128],
]

const lerp = (a: number, b: number, t: number) => a + (b - a) * t

function horaTexto(h: number) {
  const hh = Math.floor(h) % 24
  const mm = Math.floor((h % 1) * 60 / 15) * 15
  return `${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}`
}

export default function Escena({ color }: { color: Variante['id'] }) {
  const seccion = useRef<HTMLElement>(null)
  const hora = useRef<HTMLSpanElement>(null)
  const afuera = useRef<HTMLSpanElement>(null)
  const adentro = useRef<HTMLSpanElement>(null)
  const [capitulo, setCapitulo] = useState(0)
  const [quieto] = useState(() => window.matchMedia('(prefers-reduced-motion: reduce)').matches)

  useEffect(() => {
    if (quieto) return
    const el = seccion.current
    if (!el) return
    let cuadro = 0
    const n = capitulos.length - 1

    // Un solo cálculo por cuadro: el scroll se traduce en un progreso de 0 a 1
    // que mueve el sol, el cielo y los números sin volver a renderizar React.
    const pintar = () => {
      cuadro = 0
      const r = el.getBoundingClientRect()
      const recorrido = r.height - window.innerHeight
      const p = Math.min(1, Math.max(0, -r.top / recorrido))
      const x = p * n
      const i = Math.min(n - 1, Math.floor(x))
      const t = x - i
      const a = capitulos[i]
      const b = capitulos[i + 1]
      const [r1, g1, b1] = cielos[i]
      const [r2, g2, b2] = cielos[i + 1]
      el.style.setProperty('--p', p.toFixed(4))
      const rgb = [lerp(r1, r2, t), lerp(g1, g2, t), lerp(b1, b2, t)]
      el.style.setProperty('--cielo', `rgb(${rgb[0] | 0} ${rgb[1] | 0} ${rgb[2] | 0})`)
      // Con el cielo oscuro, el texto pasa a claro para mantener el contraste
      const luminancia = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
      el.style.setProperty('--texto-escena', luminancia < 140 ? '#ffffff' : '#11161a')
      if (hora.current) hora.current.textContent = horaTexto(lerp(a.hora, b.hora, t))
      if (afuera.current) afuera.current.textContent = `${Math.round(lerp(a.afuera, b.afuera, t))}°`
      if (adentro.current) adentro.current.textContent = `${Math.round(lerp(a.adentro, b.adentro, t))}°`
      setCapitulo(Math.round(x))
    }
    const alScroll = () => { if (!cuadro) cuadro = requestAnimationFrame(pintar) }
    pintar()
    window.addEventListener('scroll', alScroll, { passive: true })
    window.addEventListener('resize', alScroll)
    return () => {
      cancelAnimationFrame(cuadro)
      window.removeEventListener('scroll', alScroll)
      window.removeEventListener('resize', alScroll)
    }
  }, [quieto])

  // Sin animaciones: el mismo relato, en una lista que se lee de corrido
  if (quieto) {
    return (
      <section className="escena-quieta" aria-labelledby="titulo-escena">
        <div className="contenedor">
          <h2 id="titulo-escena">Un día de enero en Ciudad del Este</h2>
          <ol>
            {capitulos.map((c) => (
              <li key={c.titulo}>
                <h3>{c.titulo}</h3>
                <p>{c.texto}</p>
                <p className="escena-quieta__datos">Afuera {c.afuera}° · Adentro del termo {c.adentro}°</p>
              </li>
            ))}
          </ol>
        </div>
      </section>
    )
  }

  const c = capitulos[capitulo]
  return (
    <section ref={seccion} className="escena" aria-labelledby="titulo-escena">
      <div className="escena__escenario">
        <div className="escena__cielo" aria-hidden="true">
          <span className="escena__sol" />
        </div>

        <div className="escena__relato">
          <h2 id="titulo-escena" className="escena__titulo">Un día de enero en Ciudad del Este</h2>
          <div className="escena__capitulo" key={capitulo} aria-live="polite">
            <h3>{c.titulo}</h3>
            <p>{c.texto}</p>
          </div>
          <ol className="escena__avance" aria-hidden="true">
            {capitulos.map((x, i) => <li key={x.titulo} className={i <= capitulo ? 'hecho' : ''} />)}
          </ol>
        </div>

        {/* El mismo render de Blender del color elegido: la escena y el producto son uno solo */}
        <Render nombre={`estudio-${color}`} alt="" className="escena__termo" sizes="(max-width: 900px) 40vw, 26vw" ancho={1200} alto={1500} />

        <dl className="escena__datos">
          <div className="dato dato--hora">
            <dt>Hora</dt>
            <dd><span ref={hora}>07:00</span></dd>
          </div>
          <div className="dato dato--afuera">
            <dt>Afuera</dt>
            <dd><span ref={afuera}>29°</span></dd>
          </div>
          <div className="dato dato--adentro">
            <dt>Adentro del termo</dt>
            <dd><span ref={adentro}>2°</span></dd>
          </div>
        </dl>
      </div>
    </section>
  )
}
