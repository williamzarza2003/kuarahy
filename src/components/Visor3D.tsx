import { Suspense, useEffect, useLayoutEffect, useMemo, useRef } from 'react'
import { Canvas, useThree } from '@react-three/fiber'
import { ContactShadows, Environment, Lightformer, OrbitControls, useGLTF } from '@react-three/drei'
import * as THREE from 'three'
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib'
import type { Configuracion } from '../data/configuracion.ts'
import { varianteDe } from '../data/configuracion.ts'
import { dibujarGrabado, fuenteLista } from '../lib/grabado.ts'

const MODELO = '/modelos/kuarahy.glb'
// Diferencia de altura entre el cuerpo de 1,5 L y el de 1 L (en metros, igual que en blender/termo.py)
const SUBIDA_15L = 0.08
const CENTRO = new THREE.Vector3(0, 0.15, 0)

interface Props {
  config: Configuracion
  /** Giro pedido desde los botones accesibles (en grados); cambia el valor para girar otra vez */
  giro: { grados: number; n: number }
  onListo?: () => void
}

function Termo({ config, onListo }: Pick<Props, 'config' | 'onListo'>) {
  // meshopt viene incluido; sin Draco, así no se baja nada de otro dominio
  const { scene } = useGLTF(MODELO, false, true)
  const invalidar = useThree((s) => s.invalidate)
  const variante = varianteDe(config.color)

  const materiales = useMemo(() => {
    const canvas = document.createElement('canvas')
    const textura = new THREE.CanvasTexture(canvas)
    textura.flipY = false // las UV de glTF tienen el origen arriba
    textura.colorSpace = THREE.SRGBColorSpace
    textura.anisotropy = 4
    return {
      canvas,
      textura,
      pintura: new THREE.MeshPhysicalMaterial({ roughness: 0.5, clearcoat: 0.18, clearcoatRoughness: 0.4 }),
      acero: new THREE.MeshStandardMaterial({ color: '#d4d8dc', metalness: 1, roughness: 0.24 }),
      grabado: new THREE.MeshStandardMaterial({ color: '#c9ced3', metalness: 1, roughness: 0.42 }),
      goma: new THREE.MeshStandardMaterial({ color: '#1c1c1e', roughness: 0.82 }),
      nombre: new THREE.MeshStandardMaterial({ color: '#d6dade', metalness: 1, roughness: 0.4, map: textura, alphaTest: 0.5 }),
    }
  }, [])

  // Una sola vez: cada malla toma el material propio según el nombre que le puso Blender
  useLayoutEffect(() => {
    scene.traverse((o) => {
      if (!(o instanceof THREE.Mesh)) return
      // el nombre original se guarda: en desarrollo (StrictMode) este efecto corre dos veces
      o.userData.material ??= (o.material as THREE.Material).name
      const nombre = o.userData.material as string
      const m =
        nombre === 'Pintura' ? materiales.pintura
        : nombre === 'Grabado' ? materiales.grabado
        : nombre === 'Goma' ? materiales.goma
        : nombre === 'Nombre' ? materiales.nombre
        : materiales.acero
      o.material = m
      o.castShadow = true
    })
    onListo?.()
  }, [scene, materiales, onListo])

  // Color
  useLayoutEffect(() => {
    materiales.pintura.color.set(variante.base)
    materiales.pintura.needsUpdate = true
    invalidar()
  }, [variante, materiales, invalidar])

  // Tamaño y tapa: se muestran las piezas que corresponden y se sube la parte de arriba
  useLayoutEffect(() => {
    const ver = (n: string, si: boolean) => { const o = scene.getObjectByName(n); if (o) o.visible = si }
    const es15 = config.tamano === '15L'
    for (const p of ['Cuerpo', 'Manija', 'Logo', 'Nombre']) {
      ver(`${p}_1L`, !es15)
      ver(`${p}_15L`, es15)
    }
    ver('Tapa_Clasica', config.tapa === 'clasica')
    ver('Tapa_Pico', config.tapa === 'pico')
    ver('Tapa_Mate', config.tapa === 'mate')
    const sup = scene.getObjectByName('Superior')
    if (sup) sup.position.y = es15 ? SUBIDA_15L : 0
    invalidar()
  }, [scene, config.tamano, config.tapa, invalidar])

  // Nombre grabado, en vivo
  useEffect(() => {
    let vivo = true
    fuenteLista().then(() => {
      if (!vivo) return
      dibujarGrabado(materiales.canvas, config.nombre)
      materiales.textura.needsUpdate = true
      invalidar()
    })
    return () => { vivo = false }
  }, [config.nombre, materiales, invalidar])

  return <primitive object={scene} rotation={[0, THREE.MathUtils.degToRad(-12), 0]} />
}

/** Los botones "girar" de afuera del canvas mueven la cámara alrededor del termo. */
function Giro({ giro }: Pick<Props, 'giro'>) {
  const controles = useThree((s) => s.controls) as OrbitControlsImpl | null
  const invalidar = useThree((s) => s.invalidate)
  useEffect(() => {
    if (!controles || giro.n === 0) return
    const inicio = controles.getAzimuthalAngle()
    const fin = inicio + THREE.MathUtils.degToRad(giro.grados)
    const quieto = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const t0 = performance.now()
    let cuadro = 0
    const paso = (t: number) => {
      const k = quieto ? 1 : Math.min(1, (t - t0) / 450)
      const e = 1 - Math.pow(1 - k, 3)
      controles.setAzimuthalAngle(inicio + (fin - inicio) * e)
      controles.update()
      invalidar()
      if (k < 1) cuadro = requestAnimationFrame(paso)
    }
    cuadro = requestAnimationFrame(paso)
    return () => cancelAnimationFrame(cuadro)
  }, [giro, controles, invalidar])
  return null
}

/** Encuadre según el tamaño: el de 1,5 L es 8 cm más alto, así que la cámara sube y se aleja. */
function Encuadre({ tamano }: { tamano: Configuracion['tamano'] }) {
  const controles = useThree((s) => s.controls) as OrbitControlsImpl | null
  const camara = useThree((s) => s.camera)
  const invalidar = useThree((s) => s.invalidate)
  useEffect(() => {
    if (!controles) return
    const es15 = tamano === '15L'
    const objetivo = CENTRO.clone().setY(CENTRO.y + (es15 ? SUBIDA_15L / 2 : 0))
    const offset = camara.position.clone().sub(controles.target).setLength(es15 ? 1.02 : 0.88)
    controles.target.copy(objetivo)
    camara.position.copy(objetivo).add(offset)
    controles.update()
    invalidar()
  }, [tamano, controles, camara, invalidar])
  return null
}

export default function Visor3D({ config, giro, onListo }: Props) {
  const variante = varianteDe(config.color)
  const contenedor = useRef<HTMLDivElement>(null)
  return (
    <div ref={contenedor} className="visor3d__lienzo">
      <Canvas
        frameloop="demand"
        dpr={[1, 2]}
        shadows={false}
        camera={{ position: [0, 0.17, 0.88], fov: 30, near: 0.05, far: 10 }}
        gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.05 }}
        aria-hidden="true"
      >
        <Suspense fallback={null}>
          <Termo config={config} onListo={onListo} />
          {/* Estudio armado con paneles de luz: sin bajar un HDRI, reflejos de acero creíbles */}
          <Environment resolution={256}>
            <Lightformer form="rect" intensity={2.2} position={[0, 1.2, 0.4]} scale={[2, 1, 1]} rotation-x={Math.PI / 2} />
            <Lightformer form="rect" intensity={3} position={[-1.1, 0.3, 0.6]} scale={[0.5, 2.2, 1]} rotation-y={Math.PI / 2.6} />
            <Lightformer form="rect" intensity={1.6} position={[1.2, 0.3, -0.4]} scale={[0.35, 2, 1]} rotation-y={-Math.PI / 2} />
            <Lightformer form="rect" intensity={0.6} position={[0, -0.4, 1]} scale={[3, 0.6, 1]} />
            <color attach="background" args={['#3a2f2a']} />
          </Environment>
          <ContactShadows position={[0, 0, 0]} opacity={0.45} scale={0.6} blur={2.6} far={0.3} resolution={512} color={variante.sombra} />
        </Suspense>
        <OrbitControls
          makeDefault
          target={CENTRO}
          enablePan={false}
          enableZoom={false}
          enableDamping
          dampingFactor={0.12}
          rotateSpeed={0.7}
          minPolarAngle={THREE.MathUtils.degToRad(55)}
          maxPolarAngle={THREE.MathUtils.degToRad(98)}
        />
        <Giro giro={giro} />
        <Encuadre tamano={config.tamano} />
      </Canvas>
    </div>
  )
}

useGLTF.preload(MODELO, false, true)
