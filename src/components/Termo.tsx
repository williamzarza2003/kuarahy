import { useId, type CSSProperties } from 'react'
import type { Variante } from '../data/variantes.ts'

interface Props {
  variante: Variante
  className?: string
  /** Etiqueta accesible; si no se pasa, el dibujo es decorativo */
  titulo?: string
}

/**
 * El termo Kuarahy dibujado en SVG. El sombreado cilíndrico usa un degradado
 * horizontal (borde oscuro, cuerpo, brillo, cuerpo, borde) y el color sale de
 * variables CSS, así las variantes cambian sin volver a dibujar nada.
 */
export default function Termo({ variante, className = '', titulo }: Props) {
  const id = useId().replace(/:/g, '')
  const g = (n: string) => `${n}-${id}`
  const estilo = {
    '--t-base': variante.base,
    '--t-sombra': variante.sombra,
    '--t-luz': variante.luz,
    color: variante.grabado,
  } as CSSProperties

  return (
    <svg
      className={`termo ${className}`}
      viewBox="0 0 260 540"
      style={estilo}
      role={titulo ? 'img' : undefined}
      aria-label={titulo}
      aria-hidden={titulo ? undefined : true}
      focusable="false"
    >
      <defs>
        <linearGradient id={g('cuerpo')} x1="0" x2="1">
          <stop offset="0" style={{ stopColor: 'var(--t-sombra)' }} />
          <stop offset=".16" style={{ stopColor: 'var(--t-base)' }} />
          <stop offset=".3" style={{ stopColor: 'var(--t-luz)' }} />
          <stop offset=".42" style={{ stopColor: 'var(--t-base)' }} />
          <stop offset=".86" style={{ stopColor: 'var(--t-base)' }} />
          <stop offset="1" style={{ stopColor: 'var(--t-sombra)' }} />
        </linearGradient>
        <linearGradient id={g('acero')} x1="0" x2="1">
          <stop offset="0" stopColor="#7d868d" />
          <stop offset=".22" stopColor="#d9dfe3" />
          <stop offset=".34" stopColor="#ffffff" />
          <stop offset=".5" stopColor="#b9c1c7" />
          <stop offset=".85" stopColor="#9aa3aa" />
          <stop offset="1" stopColor="#6c757c" />
        </linearGradient>
        <linearGradient id={g('manija')} x1="0" x2="1">
          <stop offset="0" style={{ stopColor: 'var(--t-base)' }} />
          <stop offset="1" style={{ stopColor: 'var(--t-sombra)' }} />
        </linearGradient>
        {/* Las sombras de borde se recortan a la forma redondeada de cada pieza: sin esto,
            sus esquinas rectas asomaban como rectángulos translúcidos (sobre todo en el hombro) */}
        <clipPath id={g('forma-tapa')}><rect x="70" y="50" width="112" height="44" rx="12" /></clipPath>
        <clipPath id={g('forma-cuerpo')}><rect x="50" y="114" width="152" height="356" rx="24" /></clipPath>
        <clipPath id={g('forma-base')}><rect x="54" y="456" width="144" height="30" rx="12" /></clipPath>
        <linearGradient id={g('hombro')} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stopColor="#000" stopOpacity=".22" />
          <stop offset="1" stopColor="#000" stopOpacity="0" />
        </linearGradient>
        <radialGradient id={g('piso')} cx=".5" cy=".5" r=".5">
          <stop offset="0" stopColor="#000" stopOpacity=".35" />
          <stop offset="1" stopColor="#000" stopOpacity="0" />
        </radialGradient>
      </defs>

      {/* sombra en el piso */}
      <ellipse cx="128" cy="512" rx="112" ry="16" fill={`url(#${g('piso')})`} />

      {/* manija lateral */}
      <path
        d="M196 156 h20 a18 18 0 0 1 18 18 v176 a18 18 0 0 1 -18 18 h-20"
        fill="none" stroke={`url(#${g('manija')})`} strokeWidth="18" strokeLinecap="round"
      />
      <path d="M200 156 h16 a18 18 0 0 1 18 18 v176 a18 18 0 0 1 -18 18 h-16" fill="none" stroke="#000" strokeOpacity=".18" strokeWidth="3" />

      {/* asa de la tapa */}
      <path d="M92 58 C92 14, 160 14, 160 58" fill="none" stroke={`url(#${g('acero')})`} strokeWidth="11" strokeLinecap="round" />

      {/* tapa con pico vertedor */}
      <rect x="54" y="66" width="22" height="16" rx="5" fill={`url(#${g('acero')})`} />
      <rect x="70" y="50" width="112" height="44" rx="12" fill={`url(#${g('acero')})`} />
      <rect x="70" y="86" width="112" height="8" fill="#000" opacity=".12" clipPath={`url(#${g('forma-tapa')})`} />

      {/* collar de acero */}
      <rect x="58" y="92" width="136" height="26" rx="6" fill={`url(#${g('acero')})`} />

      {/* cuerpo */}
      <rect x="50" y="114" width="152" height="356" rx="24" fill={`url(#${g('cuerpo')})`} />
      {/* sombra suave que deja el collar sobre el hombro del cuerpo */}
      <rect x="50" y="114" width="152" height="22" fill={`url(#${g('hombro')})`} clipPath={`url(#${g('forma-cuerpo')})`} />
      {/* brillo largo, como en el acero pintado */}
      <rect x="84" y="134" width="7" height="316" rx="3.5" fill="#fff" opacity=".28" />

      {/* sol grabado: la marca */}
      <g className="termo__marca" transform="translate(126 262)">
        <circle r="17" fill="none" stroke="currentColor" strokeWidth="3" />
        {Array.from({ length: 12 }, (_, i) => (
          <line
            key={i} x1="0" y1="-24" x2="0" y2="-31" stroke="currentColor" strokeWidth="3" strokeLinecap="round"
            transform={`rotate(${i * 30})`}
          />
        ))}
        <circle r="6" fill="currentColor" />
      </g>
      <text className="termo__nombre" x="126" y="332" textAnchor="middle">KUARAHY</text>

      {/* base de acero */}
      <rect x="54" y="456" width="144" height="30" rx="12" fill={`url(#${g('acero')})`} />
      <rect x="54" y="456" width="144" height="5" fill="#000" opacity=".15" clipPath={`url(#${g('forma-base')})`} />
    </svg>
  )
}
