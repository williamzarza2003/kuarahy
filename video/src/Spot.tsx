import React from 'react'
import { AbsoluteFill, Easing, interpolate, Sequence, spring, staticFile, useCurrentFrame, useVideoConfig } from 'remotion'
import { Audio } from '@remotion/media'
import { ThreeCanvas } from '@remotion/three'
import { Termo3D } from './Termo3D'
import { COLOR, FUENTE, VARIANTES } from './marca'

export type SpotProps = {
  readonly web: string
  readonly nombreGrabado: string
}

// Duración de cada escena (30 fps). Total: 840 cuadros = 28 s
const D = { calor: 150, aparece: 150, hielo: 150, colores: 160, grabado: 110, cierre: 120 }
export const DURACION = Object.values(D).reduce((a, b) => a + b, 0)

const sujetar = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const

/** Tamaños de texto que escalan con el lado corto del cuadro (sirve igual para 16:9 y 9:16). */
function useMedidas() {
  const { width, height } = useVideoConfig()
  const corto = Math.min(width, height)
  const vertical = height > width
  return { width, height, vertical, u: corto / 1080 }
}

/** Entrada y salida suaves de cada escena (corte con fundido corto, sin efectos de más). */
function Fundido({ children, duracion, color = 'transparent' }: { children: React.ReactNode; duracion: number; color?: string }) {
  const f = useCurrentFrame()
  const opacidad = interpolate(f, [0, 8, duracion - 6, duracion], [0, 1, 1, 0], sujetar)
  return <AbsoluteFill style={{ backgroundColor: color, opacity: opacidad }}>{children}</AbsoluteFill>
}

const titulo = (u: number, tam: number): React.CSSProperties => ({
  fontFamily: FUENTE, fontWeight: 800, fontSize: tam * u, lineHeight: 0.95, letterSpacing: '-0.02em', margin: 0,
})

// ---------------------------------------------------------------- 1. Calor de enero
function Calor() {
  const f = useCurrentFrame()
  const { u, vertical, width, height } = useMedidas()
  const temp = Math.round(interpolate(f, [10, 120], [29, 41], { ...sujetar, easing: Easing.out(Easing.cubic) }))
  const cielo = interpolate(f, [0, 150], [0, 1], sujetar)
  const fondo = `color-mix(in oklab, ${COLOR.solClaro} ${Math.round((1 - cielo) * 100)}%, ${COLOR.sol})`
  const subeSol = interpolate(f, [0, 150], [0.62, 0.3], { ...sujetar, easing: Easing.out(Easing.quad) })
  const solTam = Math.min(width, height) * 0.62
  return (
    <AbsoluteFill style={{ background: fondo, overflow: 'hidden' }}>
      {/* el sol, plano como en la marca */}
      <div style={{ position: 'absolute', width: solTam, height: solTam, borderRadius: '50%', background: '#fff4d6', left: width / 2 - solTam / 2, top: height * subeSol - solTam / 2, opacity: 0.92 }} />
      {/* la ciudad, desenfocada por el calor que sube del asfalto */}
      <svg viewBox="0 0 1000 220" preserveAspectRatio="none" style={{ position: 'absolute', left: 0, bottom: 0, width: '100%', height: height * 0.26, filter: `url(#calor) blur(${3 * u}px)` }}>
        <defs>
          <filter id="calor">
            <feTurbulence type="fractalNoise" baseFrequency={`0.012 ${0.06 + 0.01 * Math.sin(f / 7)}`} numOctaves={2} seed={Math.floor(f / 2)} />
            <feDisplacementMap in="SourceGraphic" scale={14} />
          </filter>
        </defs>
        <path fill={COLOR.solOscuro} d="M0 220 V140 h60 v-40 h40 v60 h50 V70 h70 v90 h40 v-50 h60 v-30 h50 v80 h40 V60 h80 v100 h50 v-40 h60 v-60 h70 v120 h40 v-70 h60 v70 h70 V90 h60 v50 h40 v-30 h50 v110 Z" />
      </svg>
      <div style={{ position: 'absolute', left: 90 * u, right: 90 * u, top: (vertical ? 180 : 100) * u, color: COLOR.tinta }}>
        <p style={{ fontFamily: FUENTE, fontWeight: 600, fontSize: 46 * u, margin: 0 }}>Enero en Ciudad del Este</p>
        <p style={{ ...titulo(u, vertical ? 360 : 300), fontVariantNumeric: 'tabular-nums', marginTop: 10 * u }}>{temp}°</p>
        <p style={{ fontFamily: FUENTE, fontWeight: 600, fontSize: 52 * u, margin: 0 }}>afuera</p>
      </div>
    </AbsoluteFill>
  )
}

// ---------------------------------------------------------------- 2. El termo en contraluz
function Aparece() {
  const f = useCurrentFrame()
  const { width, height, u, vertical } = useMedidas()
  const giro = interpolate(f, [0, 150], [-160, 20], { ...sujetar, easing: Easing.inOut(Easing.cubic) })
  const acerca = interpolate(f, [0, 150], [1.06, 0.82], { ...sujetar, easing: Easing.out(Easing.cubic) })
  const brillo = interpolate(f, [0, 40], [0, 1], sujetar)
  return (
    <AbsoluteFill style={{ background: COLOR.noche, overflow: 'hidden' }}>
      <AbsoluteFill style={{ opacity: brillo, left: vertical ? 0 : width * 0.2 }}>
        <ThreeCanvas width={width} height={height} camera={{ fov: vertical ? 34 : 24 }} gl={{ toneMapping: 4, toneMappingExposure: 1.1 }}>
          <Termo3D color="#e0518d" giro={giro} luz="contraluz" camara={{ distancia: acerca, altura: 0.14, objetivo: 0.15 }} />
        </ThreeCanvas>
      </AbsoluteFill>
      <p style={{ position: 'absolute', left: 90 * u, bottom: (vertical ? 200 : 90) * u, margin: 0, color: '#c5d3da', fontFamily: FUENTE, fontWeight: 600, fontSize: 46 * u, opacity: interpolate(f, [70, 95], [0, 1], sujetar) }}>
        Acero de doble pared, hecho en Paraguay.
      </p>
    </AbsoluteFill>
  )
}

// ---------------------------------------------------------------- 3. Hielo: 3° adentro
const CUBOS = [
  { x: -0.085, z: 0.05, entra: 0, giro: 0.6, tam: 0.026 },
  { x: 0.09, z: 0.03, entra: 12, giro: -0.9, tam: 0.03 },
  { x: -0.045, z: 0.1, entra: 24, giro: 1.4, tam: 0.024 },
  { x: 0.05, z: 0.11, entra: 36, giro: 0.3, tam: 0.028 },
]
const ALTURA_INICIAL = 0.45
const GRAVEDAD = 1.6 // m/s² "de cámara lenta": se ve caer, como en un comercial

function Cubo({ x, z, entra, giro, tam }: (typeof CUBOS)[number]) {
  const f = useCurrentFrame()
  const t = Math.max(0, (f - entra) / 30)
  const piso = tam / 2
  const caida = ALTURA_INICIAL - 0.5 * GRAVEDAD * t * t
  const tPiso = Math.sqrt((2 * (ALTURA_INICIAL - piso)) / GRAVEDAD)
  // al tocar el piso: un rebote chico que se apaga, y queda quieto
  const tr = t - tPiso
  const y = caida > piso ? caida : piso + Math.abs(Math.sin(tr * 9)) * 0.012 * Math.exp(-tr * 6)
  const vuelta = Math.min(t, tPiso)
  return (
    <mesh position={[x, y, z]} rotation={[vuelta * giro * 2, vuelta * giro, 0]}>
      <boxGeometry args={[tam, tam, tam]} />
      <meshPhysicalMaterial color="#d8f3ff" transmission={0.9} roughness={0.12} thickness={0.03} ior={1.31} attenuationColor="#9fdcf5" attenuationDistance={0.05} />
    </mesh>
  )
}

function Hielo() {
  const f = useCurrentFrame()
  const { width, height, u, vertical } = useMedidas()
  const entra = spring({ frame: f - 30, fps: 30, config: { damping: 14 } })
  return (
    <AbsoluteFill style={{ background: COLOR.hielo, overflow: 'hidden' }}>
      <AbsoluteFill style={{ top: vertical ? height * 0.16 : 0 }}>
        <ThreeCanvas width={width} height={height} camera={{ fov: vertical ? 34 : 26 }} gl={{ toneMapping: 4 }}>
          <Termo3D color="#1d6ea3" giro={-25 + f * 0.12} camara={{ distancia: 0.88, altura: 0.18, objetivo: 0.155 }} />
          {CUBOS.map((c, i) => <Cubo key={i} {...c} />)}
        </ThreeCanvas>
      </AbsoluteFill>
      {CUBOS.map((c, i) => (
        <Sequence key={i} from={c.entra + 22} durationInFrames={20} layout="none">
          <Audio src={staticFile('sonido/hielo.wav')} volume={0.6} />
        </Sequence>
      ))}
      <div style={{ position: 'absolute', left: 90 * u, top: (vertical ? 180 : 110) * u, color: COLOR.noche, transform: `translateY(${(1 - entra) * 40 * u}px)`, opacity: entra }}>
        <p style={{ ...titulo(u, vertical ? 360 : 280), fontVariantNumeric: 'tabular-nums' }}>3°</p>
        <p style={{ fontFamily: FUENTE, fontWeight: 600, fontSize: 52 * u, margin: 0 }}>adentro, a las tres de la tarde</p>
      </div>
    </AbsoluteFill>
  )
}

// ---------------------------------------------------------------- 4. Los cinco colores, en ritmo
function Colores() {
  const f = useCurrentFrame()
  const { width, height, u, vertical } = useMedidas()
  const tramo = D.colores / VARIANTES.length
  const i = Math.min(VARIANTES.length - 1, Math.floor(f / tramo))
  const v = VARIANTES[i]
  const golpe = spring({ frame: f - i * tramo, fps: 30, config: { damping: 11, stiffness: 180 } })
  return (
    <AbsoluteFill style={{ background: v.fondo, overflow: 'hidden' }}>
      <AbsoluteFill style={{ top: vertical ? -height * 0.1 : 0, left: vertical ? 0 : width * 0.08 }}>
        <ThreeCanvas width={width} height={height} camera={{ fov: vertical ? 34 : 26 }} gl={{ toneMapping: 4 }}>
          <Termo3D color={v.base} giro={-30 + f * 0.9} camara={{ distancia: 0.9 - golpe * 0.04, altura: 0.17, objetivo: 0.15 }} />
        </ThreeCanvas>
      </AbsoluteFill>
      {VARIANTES.map((_, k) => (
        <Sequence key={k} from={Math.round(k * tramo)} durationInFrames={8} layout="none">
          <Audio src={staticFile('sonido/tic.wav')} volume={0.5} />
        </Sequence>
      ))}
      <div style={{ position: 'absolute', left: 90 * u, bottom: (vertical ? 220 : 100) * u, color: COLOR.tinta }}>
        <p style={{ fontFamily: FUENTE, fontWeight: 600, fontSize: 44 * u, margin: 0 }}>{i + 1} de 5 · colores de acá</p>
        <p style={{ ...titulo(u, vertical ? 200 : 170), transform: `scale(${0.94 + golpe * 0.06})`, transformOrigin: 'left bottom' }}>{v.nombre}</p>
      </div>
    </AbsoluteFill>
  )
}

// ---------------------------------------------------------------- 5. El grabado con un nombre
function Grabado({ nombre }: { nombre: string }) {
  const f = useCurrentFrame()
  const { width, height, u, vertical } = useMedidas()
  const letras = Math.min(nombre.length, Math.floor(interpolate(f, [12, 70], [0, nombre.length], sujetar)))
  return (
    <AbsoluteFill style={{ background: COLOR.noche2, overflow: 'hidden' }}>
      <AbsoluteFill style={{ left: vertical ? 0 : width * 0.22, top: vertical ? height * 0.24 : 0 }}>
      <ThreeCanvas width={width} height={height} camera={{ fov: vertical ? 26 : 18 }} gl={{ toneMapping: 4, toneMappingExposure: 1.1 }}>
        <Termo3D color="#2a2d33" giro={-6 + f * 0.05} nombre={nombre.slice(0, letras)} camara={{ distancia: 0.34, altura: 0.1, objetivo: 0.092 }} />
      </ThreeCanvas>
      </AbsoluteFill>
      <div style={{ position: 'absolute', left: 90 * u, right: 90 * u, top: (vertical ? 180 : 90) * u, color: '#fff' }}>
        <p style={{ ...titulo(u, vertical ? 120 : 96) }}>Con tu nombre,</p>
        <p style={{ ...titulo(u, vertical ? 120 : 96), color: COLOR.hielo }}>grabado con láser.</p>
      </div>
    </AbsoluteFill>
  )
}

// ---------------------------------------------------------------- 6. Cierre
function Cierre({ web }: { web: string }) {
  const f = useCurrentFrame()
  const { width, height, u, vertical } = useMedidas()
  const entra = spring({ frame: f - 6, fps: 30, config: { damping: 16 } })
  const solTam = Math.min(width, height) * 0.78
  return (
    <AbsoluteFill style={{ background: COLOR.sol }}>
      <div style={{ position: 'absolute', width: solTam, height: solTam, borderRadius: '50%', background: COLOR.solClaro, left: vertical ? width / 2 - solTam / 2 : width * 0.68 - solTam / 2, top: vertical ? height * 0.6 - solTam / 2 : height / 2 - solTam / 2 }} />
      <AbsoluteFill style={vertical ? { top: height * 0.22 } : { left: width * 0.2 }}>
        <ThreeCanvas width={width} height={height} camera={{ fov: vertical ? 30 : 26 }} gl={{ toneMapping: 4 }}>
          <Termo3D color="#e0518d" giro={-24 + f * 0.15} camara={{ distancia: 0.88, altura: 0.17, objetivo: 0.15 }} />
        </ThreeCanvas>
      </AbsoluteFill>
      <div style={{ position: 'absolute', left: 90 * u, top: (vertical ? 170 : 0) * u, bottom: vertical ? undefined : 0, display: 'flex', flexDirection: 'column', justifyContent: 'center', color: COLOR.tinta, maxWidth: vertical ? width - 180 * u : width * 0.5, opacity: entra, transform: `translateY(${(1 - entra) * 30 * u}px)` }}>
        <p style={{ ...titulo(u, vertical ? 150 : 130) }}>Kuarahy.</p>
        <p style={{ ...titulo(u, vertical ? 92 : 80), fontWeight: 800, marginTop: 18 * u }}>El termo que le gana al sol.</p>
        <p style={{ fontFamily: FUENTE, fontWeight: 600, fontSize: 46 * u, margin: `${34 * u}px 0 0` }}>{web}</p>
      </div>
    </AbsoluteFill>
  )
}

export const Spot: React.FC<SpotProps> = ({ web, nombreGrabado }) => {
  let t = 0
  const desde = (d: number) => { const a = t; t += d; return a }
  return (
    <AbsoluteFill style={{ backgroundColor: COLOR.noche }}>
      <Sequence name="Calor de enero" from={desde(D.calor)} durationInFrames={D.calor}>
        <Fundido duracion={D.calor}><Calor /></Fundido>
        <Audio src={staticFile('sonido/calor.wav')} volume={0.7} />
      </Sequence>
      <Sequence name="El termo en contraluz" from={desde(D.aparece)} durationInFrames={D.aparece}>
        <Fundido duracion={D.aparece}><Aparece /></Fundido>
        <Audio src={staticFile('sonido/whoosh.wav')} volume={0.6} />
      </Sequence>
      <Sequence name="Hielo, 3° adentro" from={desde(D.hielo)} durationInFrames={D.hielo}>
        <Fundido duracion={D.hielo}><Hielo /></Fundido>
      </Sequence>
      <Sequence name="Cinco colores" from={desde(D.colores)} durationInFrames={D.colores}>
        <Fundido duracion={D.colores}><Colores /></Fundido>
      </Sequence>
      <Sequence name="Grabado" from={desde(D.grabado)} durationInFrames={D.grabado}>
        <Fundido duracion={D.grabado}><Grabado nombre={nombreGrabado} /></Fundido>
      </Sequence>
      <Sequence name="Cierre" from={desde(D.cierre)} durationInFrames={D.cierre}>
        <Cierre web={web} />
        <Audio src={staticFile('sonido/cierre.wav')} volume={0.8} />
      </Sequence>
    </AbsoluteFill>
  )
}
