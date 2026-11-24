import { useRef, useState } from 'react'
import Render from './Render.tsx'

const fotos = [
  { nombre: 'hero-lapacho', ancho: 1920, alto: 1200, alt: 'Termo Lapacho con gotas de condensación junto a una guampa de palo santo con yerba y hielo, sobre fondo naranja con luz dura de mediodía', pie: 'Lapacho, con la guampa cargada. Luz dura de mediodía.' },
  { nombre: 'macro-grabado', ancho: 1600, alto: 1200, alt: 'Detalle del sol y la palabra KUARAHY grabados con láser sobre la pintura azul Paraná', pie: 'El sol y el nombre, grabados con láser: la pintura se va y queda el acero.' },
  { nombre: 'macro-pico', ancho: 1600, alto: 1200, alt: 'Detalle de la tapa con pico cebador de acero y la tapita de goma abierta', pie: 'Tapa con pico cebador: sirve de a poco, con una mano.' },
  { nombre: 'ambiente-monte', ancho: 1800, alto: 1200, alt: 'Termo verde Monte sobre una mesa de madera al aire libre con una guampa y yuyos', pie: 'Monte, en la mesa del patio.' },
  { nombre: 'estudio-carbon', ancho: 1200, alto: 1500, alt: 'Termo Kuarahy negro Carbón en estudio, con el grabado en acero', pie: 'Carbón: negro mate que no muestra la tierra colorada.' },
  { nombre: 'estudio-siesta', ancho: 1200, alto: 1500, alt: 'Termo Kuarahy naranja Siesta en estudio', pie: 'Siesta, el naranja de las tres de la tarde.' },
]

/** Fotos de producto renderizadas en Blender. Al tocar una, se abre grande (con zoom del navegador). */
export default function Galeria() {
  const dialogo = useRef<HTMLDialogElement>(null)
  const [abierta, setAbierta] = useState<(typeof fotos)[number] | null>(null)

  const abrir = (f: (typeof fotos)[number]) => {
    setAbierta(f)
    dialogo.current?.showModal()
  }

  return (
    <section id="fotos" className="galeria" aria-labelledby="titulo-galeria">
      <div className="contenedor">
        <div className="galeria__cabecera">
          <h2 id="titulo-galeria">Fotos</h2>
          <p>Todas salen del mismo modelo 3D que podés girar más arriba, renderizado en Blender.</p>
        </div>
        <ul className="galeria__grilla">
          {fotos.map((f, i) => (
            <li key={f.nombre} className={`galeria__item galeria__item--${i}`}>
              <button type="button" className="galeria__boton" onClick={() => abrir(f)} aria-label={`Ver más grande: ${f.pie}`}>
                <Render nombre={f.nombre} alt={f.alt} ancho={f.ancho} alto={f.alto} sizes={i === 0 ? '(max-width: 720px) 92vw, 66vw' : '(max-width: 720px) 92vw, 33vw'} />
              </button>
            </li>
          ))}
        </ul>
      </div>

      <dialog ref={dialogo} className="zoom" onClose={() => setAbierta(null)} aria-label={abierta?.pie ?? 'Foto'}>
        <form method="dialog" className="zoom__barra">
          <p>{abierta?.pie}</p>
          <button className="zoom__cerrar">Cerrar</button>
        </form>
        {abierta && (
          <div className="zoom__lienzo">
            <picture>
              <source type="image/avif" srcSet={`/img/renders/${abierta.nombre}-1920.avif 1920w, /img/renders/${abierta.nombre}-1200.avif 1200w`} sizes="100vw" />
              <img
                src={`/img/renders/${abierta.nombre}-1200.webp`}
                srcSet={`/img/renders/${abierta.nombre}-1920.webp 1920w, /img/renders/${abierta.nombre}-1200.webp 1200w`}
                sizes="100vw"
                width={abierta.ancho}
                height={abierta.alto}
                alt={abierta.alt}
              />
            </picture>
          </div>
        )}
      </dialog>
    </section>
  )
}
