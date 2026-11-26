interface Props {
  /** Nombre base en public/img/renders (se sirven -640/-1200 en AVIF y WebP) */
  nombre: string
  alt: string
  ancho: number
  alto: number
  sizes: string
  className?: string
  prioridad?: boolean
}

/** Un render de Blender: AVIF con respaldo WebP, dos tamaños y espacio reservado (sin saltos). */
export default function Render({ nombre, alt, ancho, alto, sizes, className = '', prioridad = false }: Props) {
  const base = `/img/renders/${nombre}`
  return (
    <picture className={className}>
      <source type="image/avif" srcSet={`${base}-640.avif 640w, ${base}-1200.avif 1200w`} sizes={sizes} />
      <img
        src={`${base}-1200.webp`}
        srcSet={`${base}-640.webp 640w, ${base}-1200.webp 1200w`}
        sizes={sizes}
        width={ancho}
        height={alto}
        alt={alt}
        loading={prioridad ? 'eager' : 'lazy'}
        fetchPriority={prioridad ? 'high' : 'auto'}
        decoding="async"
      />
    </picture>
  )
}
