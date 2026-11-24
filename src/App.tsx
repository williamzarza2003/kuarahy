import { useEffect, useState, type FormEvent } from 'react'
import Escena from './components/Escena.tsx'
import Personalizador from './components/Personalizador.tsx'
import Galeria from './components/Galeria.tsx'
import VideoSpot from './components/VideoSpot.tsx'
import Confianza from './components/Confianza.tsx'
import Render from './components/Render.tsx'
import { aURL, desdeURL, guaranies, precio, varianteDe, type Configuracion } from './data/configuracion.ts'

const ficha = [
  { dato: 'Capacidad', valor: '1 L o 1,5 L', nota: 'Una ronda para cuatro, o la larga de la siesta' },
  { dato: 'Hielo', valor: '24 horas', nota: 'Con el termo lleno a la sombra, a 40°' },
  { dato: 'Agua fría', valor: '36 horas', nota: 'Debajo de 10° sin hielo extra' },
  { dato: 'Material', valor: 'Acero 304', nota: 'Doble pared al vacío, sin plástico en contacto con el agua' },
  { dato: 'Boca', valor: '8,5 cm', nota: 'Entran los cubitos grandes de la heladera' },
  { dato: 'Tapa', valor: 'Clásica o pico', nota: 'Con asa plegable, o con pico cebador para servir con una mano' },
  { dato: 'Peso vacío', valor: '560 g', nota: 'Con manija lateral de agarre' },
  { dato: 'Garantía', valor: '2 años', nota: 'Si pierde el vacío, te damos otro' },
]

/** Temperatura del agua según la hora, con el termo cargado a las 7 con 2° */
function tempComun(h: number) { return Math.min(29, 2 + Math.max(0, h - 7) * 2.8) }
function tempKuarahy(h: number) { return 2 + Math.max(0, h - 7) * 0.14 }
function hieloComun(h: number) { return Math.max(0, 1 - (h - 7) / 4.3) }
function hieloKuarahy(h: number) { return Math.max(0, 1 - (h - 7) / 30) }

function Hielo({ cantidad, etiqueta }: { cantidad: number; etiqueta: string }) {
  const cubos = Math.round(cantidad * 6)
  return (
    <div className="hielo" role="img" aria-label={etiqueta}>
      {Array.from({ length: 6 }, (_, i) => <span key={i} className={i < cubos ? 'cubo' : 'cubo cubo--derretido'} />)}
    </div>
  )
}

function Termometro({ temp }: { temp: number }) {
  const alto = Math.min(100, (temp / 30) * 100)
  return (
    <div className="termometro" aria-hidden="true">
      <span className="termometro__nivel" style={{ height: `${alto}%` }} />
    </div>
  )
}

export default function App() {
  const [config, setConfig] = useState<Configuracion>(() => desdeURL(location.search))
  const [hora, setHora] = useState(15)
  const [anotado, setAnotado] = useState<{ nombre: string; resumen: string } | null>(null)
  const [error, setError] = useState('')
  const variante = varianteDe(config.color)

  // El diseño vive en la URL: se puede compartir o volver a él con atrás/adelante
  useEffect(() => {
    const url = `${location.pathname}${aURL(config)}${location.hash}`
    if (url !== `${location.pathname}${location.search}${location.hash}`) history.replaceState(null, '', url)
  }, [config])

  const resumen = `${variante.nombre} de ${config.tamano === '15L' ? '1,5 L' : '1 L'}, tapa ${config.tapa === 'pico' ? 'con pico cebador' : 'clásica'}${config.nombre.trim() ? ` y «${config.nombre.trim()}» grabado` : ''}`

  const anotar = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const datos = new FormData(e.currentTarget)
    const nombre = String(datos.get('nombre') || '').trim()
    const contacto = String(datos.get('contacto') || '').trim()
    if (nombre.length < 2) return setError('Contanos tu nombre para saber a quién avisarle.')
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(contacto) && !/^\+?[\d\s-]{8,}$/.test(contacto)) {
      return setError('Dejanos un email o un número de WhatsApp con código de área, por ejemplo 0981 123 456.')
    }
    setError('')
    setAnotado({ nombre: nombre.split(' ')[0], resumen })
  }

  const h = hora
  const comun = tempComun(h)
  const kuarahy = tempKuarahy(h)

  return (
    <>
      <a href="#contenido" className="saltar">Ir al contenido</a>
      <header className="barra">
        <a href="#inicio" className="logo" aria-label="Kuarahy, inicio">
          <span className="logo__sol" aria-hidden="true" />
          Kuarahy
        </a>
        <nav aria-label="Secciones">
          <a href="#hacelo">Hacé el tuyo</a>
          <a href="#fotos">Fotos</a>
          <a href="#ficha">Ficha</a>
          <a href="#quiero" className="boton boton--chico">Quiero el mío</a>
        </nav>
      </header>

      <main id="contenido">
        <section id="inicio" className="portada">
          <div className="portada__texto">
            <p className="portada__guarani"><span lang="gn">Kuarahy</span>: sol, en guaraní.</p>
            <h1>El termo que le gana al sol.</h1>
            <p className="portada__bajada">
              Acero de doble pared hecho en Paraguay para la ronda de tereré. El hielo dura 24 horas
              aunque afuera haga 40°.
            </p>
            <div className="portada__acciones">
              <a href="#hacelo" className="boton">Armá el tuyo</a>
              <a href="#fotos" className="enlace">Ver las fotos</a>
            </div>
          </div>
          <div className="portada__producto">
            <Render
              nombre={`estudio-${config.color}`}
              alt={`Termo Kuarahy color ${variante.nombre}, con manija lateral y tapa de acero`}
              className="portada__termo"
              sizes="(max-width: 900px) 70vw, 40vw"
              ancho={1200}
              alto={1500}
              prioridad
            />
          </div>
        </section>

        <Escena color={config.color} />

        <Personalizador config={config} setConfig={setConfig} />

        <Galeria />

        <VideoSpot />

        <section className="comparacion" aria-labelledby="titulo-comparacion">
          <div className="contenedor">
            <h2 id="titulo-comparacion">Con y sin Kuarahy, un día de enero</h2>
            <p className="comparacion__bajada">Los dos termos se llenaron a las 7 con hielo y agua a 2°. Mové la hora.</p>
            <label className="reloj">
              <span>Hora: <output>{String(Math.floor(h)).padStart(2, '0')}:{h % 1 ? '30' : '00'}</output></span>
              <input type="range" min={7} max={20} step={0.5} value={h} onChange={(e) => setHora(Number(e.target.value))} />
            </label>
            <div className="duelo">
              <article className="duelo__lado duelo__lado--comun">
                <h3>Termo común</h3>
                <div className="duelo__lectura">
                  <Termometro temp={comun} />
                  <p className="duelo__temp">{Math.round(comun)}°</p>
                </div>
                <Hielo cantidad={hieloComun(h)} etiqueta={hieloComun(h) ? 'Queda algo de hielo' : 'Sin hielo'} />
                <p>{hieloComun(h) ? 'El hielo se va rápido.' : 'Sin hielo desde las 11:20. El agua ya está tibia.'}</p>
              </article>
              <article className="duelo__lado duelo__lado--kuarahy">
                <h3>Kuarahy</h3>
                <div className="duelo__lectura">
                  <Termometro temp={kuarahy} />
                  <p className="duelo__temp">{Math.round(kuarahy)}°</p>
                </div>
                <Hielo cantidad={hieloKuarahy(h)} etiqueta="El hielo sigue casi entero" />
                <p>El hielo sigue entero. El tereré sale igual que a la mañana.</p>
              </article>
            </div>
            <p className="nota">Valores de referencia de un producto ficticio, a la sombra y con 40° de máxima.</p>
          </div>
        </section>

        <section className="equipo" aria-labelledby="titulo-equipo">
          <div className="contenedor equipo__grilla">
            <Render
              nombre="ambiente-monte"
              alt="Termo Kuarahy verde Monte sobre una mesa de madera al aire libre, junto a una guampa con bombilla y ramitos de yuyos"
              className="equipo__foto"
              sizes="(max-width: 900px) 92vw, 50vw"
              ancho={1800}
              alto={1200}
            />
            <div>
              <h2 id="titulo-equipo">La guampa y la bombilla, también</h2>
              <p>
                El equipo completo trae una guampa de palo santo torneada en Luque, con virolas de acero
                para que no se raje, y una bombilla de acero con filtro que se desarma para lavarla bien.
              </p>
              <ul className="equipo__lista">
                <li><strong>Guampa de palo santo</strong> con el perfume de la madera, que se cura con el uso.</li>
                <li><strong>Bombilla desarmable</strong>: el filtro se desenrosca y no junta yerba.</li>
                <li><strong>Funda de lona</strong> con correa para llevar todo a la cancha o a la facultad.</li>
              </ul>
              <p className="equipo__precio"><strong>+{guaranies(100_000)}</strong> sobre el termo que elijas.</p>
            </div>
          </div>
        </section>

        <section id="ficha" className="ficha" aria-labelledby="titulo-ficha">
          <div className="contenedor">
            <h2 id="titulo-ficha">Ficha técnica</h2>
            <dl className="ficha__lista">
              {ficha.map((f) => (
                <div key={f.dato} className="ficha__fila">
                  <dt>{f.dato}</dt>
                  <dd>
                    <strong>{f.valor}</strong>
                    <span>{f.nota}</span>
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        </section>

        <Confianza />

        <section id="quiero" className="quiero" aria-labelledby="titulo-quiero">
          <div className="contenedor quiero__grilla">
            <div>
              <h2 id="titulo-quiero">Quiero el mío</h2>
              <p>
                La primera tanda sale en diciembre, antes de las fiestas. Anotate y te avisamos cuando
                esté para retirar o para enviar.
              </p>
              <div className="quiero__diseno">
                <Render nombre={`estudio-${config.color}`} alt="" className="quiero__miniatura" sizes="96px" ancho={1200} alto={1500} />
                <p>
                  <span>Tu diseño</span>
                  <strong>{resumen}</strong>
                  <span>{guaranies(precio(config))} · <a href="#hacelo">Cambiarlo</a></span>
                </p>
              </div>
            </div>
            {anotado ? (
              <div className="anotado" role="status">
                <h3>Listo, {anotado.nombre}.</h3>
                <p>Te anotamos para el {anotado.resumen}. Te escribimos cuando salga la primera tanda.</p>
                <p className="nota">Demo de portafolio: no se guardó ningún dato.</p>
              </div>
            ) : (
              <form className="formulario" onSubmit={anotar} noValidate>
                <label>
                  Nombre
                  <input name="nombre" autoComplete="given-name" />
                </label>
                <label>
                  Email o WhatsApp
                  <input name="contacto" autoComplete="email" />
                </label>
                {error && <p className="error" role="alert">{error}</p>}
                <button className="boton">Anotarme con este diseño</button>
              </form>
            )}
          </div>
        </section>
      </main>

      <footer className="pie">
        <div className="contenedor pie__grilla">
          <p className="pie__marca"><span className="logo__sol" aria-hidden="true" /> Kuarahy</p>
          <p>
            Producto y marca ficticios, hechos como proyecto de portafolio por{' '}
            <a href="https://github.com/williamzarza2003">William Zarza</a>. Modelo 3D, fotos y video hechos con
            Blender y Remotion a partir del mismo modelo.
          </p>
        </div>
      </footer>
    </>
  )
}
