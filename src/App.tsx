import { useState, type FormEvent } from 'react'
import Termo from './components/Termo.tsx'
import Escena from './components/Escena.tsx'
import { Guampa } from './components/Equipo.tsx'
import { variantes, type Variante } from './data/variantes.ts'

const ficha = [
  { dato: 'Capacidad', valor: '1,2 litros', nota: 'Una ronda larga para cinco' },
  { dato: 'Hielo', valor: '24 horas', nota: 'Con el termo lleno a la sombra, a 40°' },
  { dato: 'Agua fría', valor: '36 horas', nota: 'Debajo de 10° sin hielo extra' },
  { dato: 'Material', valor: 'Acero 304', nota: 'Doble pared al vacío, sin plástico en contacto con el agua' },
  { dato: 'Boca', valor: '5,5 cm', nota: 'Entran los cubitos grandes de la heladera' },
  { dato: 'Pico', valor: 'Vertedor', nota: 'Sirve de a poco, con una mano, sin abrir la tapa' },
  { dato: 'Peso vacío', valor: '540 g', nota: 'Con manija lateral de agarre' },
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
  const [variante, setVariante] = useState<Variante>(variantes[0])
  const [hora, setHora] = useState(15)
  const [anotado, setAnotado] = useState<{ nombre: string; color: string } | null>(null)
  const [error, setError] = useState('')

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
    setAnotado({ nombre: nombre.split(' ')[0], color: variante.nombre })
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
          <a href="#colores">Colores</a>
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
              <a href="#quiero" className="boton">Quiero el mío</a>
              <a href="#colores" className="enlace">Ver los cinco colores</a>
            </div>
          </div>
          <div className="portada__producto">
            <Termo variante={variante} titulo={`Termo Kuarahy color ${variante.nombre}`} className="portada__termo" />
          </div>
        </section>

        <Escena variante={variante} />

        <section id="colores" className="colores" aria-labelledby="titulo-colores">
          <div className="contenedor colores__grilla">
            <div className="colores__muestra">
              <Termo variante={variante} titulo={`Termo Kuarahy color ${variante.nombre}`} />
            </div>
            <div>
              <h2 id="titulo-colores">Cinco colores, todos de acá</h2>
              <fieldset className="selector">
                <legend className="sr-only">Elegí un color</legend>
                {variantes.map((v) => (
                  <label key={v.id} className={v.id === variante.id ? 'swatch swatch--activo' : 'swatch'}>
                    <input type="radio" name="color" value={v.id} checked={v.id === variante.id} onChange={() => setVariante(v)} />
                    <span className="swatch__color" style={{ background: v.base }} aria-hidden="true" />
                    <span className="swatch__nombre">{v.nombre}</span>
                  </label>
                ))}
              </fieldset>
              <p className="colores__nota" aria-live="polite">
                <strong>{variante.nombre}.</strong> {variante.nota}
              </p>
            </div>
          </div>
        </section>

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
            <div className="equipo__dibujo">
              <Guampa />
            </div>
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

        <section id="quiero" className="quiero" aria-labelledby="titulo-quiero">
          <div className="contenedor quiero__grilla">
            <div>
              <h2 id="titulo-quiero">Quiero el mío</h2>
              <p>
                La primera tanda sale en diciembre, antes de las fiestas. Anotate y te avisamos cuando
                esté para retirar o para enviar.
              </p>
              <p className="quiero__precio"><strong>₲ 289.000</strong> el termo · <strong>₲ 389.000</strong> el equipo completo</p>
            </div>
            {anotado ? (
              <div className="anotado" role="status">
                <Termo variante={variante} className="anotado__termo" />
                <div>
                  <h3>Listo, {anotado.nombre}.</h3>
                  <p>Te anotamos para el {anotado.color}. Te escribimos cuando salga la primera tanda.</p>
                  <p className="nota">Demo de portafolio: no se guardó ningún dato.</p>
                </div>
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
                <label>
                  Color
                  <select value={variante.id} onChange={(e) => setVariante(variantes.find((v) => v.id === e.target.value)!)}>
                    {variantes.map((v) => <option key={v.id} value={v.id}>{v.nombre}</option>)}
                  </select>
                </label>
                {error && <p className="error" role="alert">{error}</p>}
                <button className="boton">Anotarme en la lista</button>
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
            <a href="https://github.com/williamzarza2003">William Zarza</a>. Ilustraciones en SVG propias.
          </p>
        </div>
      </footer>
    </>
  )
}
