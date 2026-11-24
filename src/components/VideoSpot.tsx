import { useEffect, useRef, useState } from 'react'

/**
 * El spot de 28 s hecho con Remotion a partir del mismo modelo 3D.
 * En celular vertical se sirve el corte 9:16; en el resto, el 16:9.
 * No se baja nada hasta que la sección está cerca (preload="none" + IntersectionObserver).
 */
export default function VideoSpot() {
  const seccion = useRef<HTMLElement>(null)
  const [vertical] = useState(() => matchMedia('(max-width: 700px) and (orientation: portrait)').matches)
  const [cerca, setCerca] = useState(false)
  const formato = vertical ? '9x16' : '16x9'

  useEffect(() => {
    const el = seccion.current
    if (!el) return
    const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setCerca(true); obs.disconnect() } }, { rootMargin: '300px 0px' })
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  return (
    <section ref={seccion} className="spot" aria-labelledby="titulo-spot">
      <div className="contenedor spot__grilla">
        <div className="spot__texto">
          <h2 id="titulo-spot">El comercial</h2>
          <p>
            28 segundos armados con Remotion: el mismo termo 3D de las fotos, animado cuadro por cuadro con código.
            Sin música, con sonido diseñado a partir de ruido y tonos.
          </p>
        </div>
        <video
          className={`spot__video spot__video--${formato}`}
          controls
          muted
          playsInline
          preload="none"
          poster={`/video/kuarahy-spot-${formato}.webp`}
          width={vertical ? 1080 : 1920}
          height={vertical ? 1920 : 1080}
          aria-label="Comercial de Kuarahy: el calor de enero, el termo en contraluz, el hielo a 3 grados, los cinco colores y el grabado con un nombre"
        >
          {cerca && <source src={`/video/kuarahy-spot-${formato}.mp4`} type="video/mp4" />}
        </video>
      </div>
    </section>
  )
}
