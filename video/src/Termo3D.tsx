import { useLayoutEffect, useMemo } from 'react'
import { useGLTF, Environment, Lightformer } from '@react-three/drei'
import { useThree } from '@react-three/fiber'
import * as THREE from 'three'
import { staticFile } from 'remotion'
import { FUENTE } from './marca'

const MODELO = staticFile('kuarahy.glb')

export interface Termo3DProps {
  color: string
  /** Giro alrededor del eje vertical, en grados */
  giro: number
  nombre?: string
  tapa?: 'clasica' | 'pico' | 'mate'
  /** estudio: luz pareja · contraluz: silueta con borde de luz */
  luz?: 'estudio' | 'contraluz'
  camara: { distancia: number; altura: number; objetivo: number }
}

/** Dibuja el nombre en el canvas de la banda (mismo criterio que la web: src/lib/grabado.ts). */
function dibujar(canvas: HTMLCanvasElement, nombre: string) {
  canvas.width = 1400
  canvas.height = 300
  const ctx = canvas.getContext('2d')!
  ctx.clearRect(0, 0, 1400, 300)
  if (!nombre.trim()) return
  let tam = 230
  ctx.font = `800 ${tam}px "${FUENTE}"`
  const ancho = ctx.measureText(nombre).width
  if (ancho > 1200) tam = Math.floor((tam * 1200) / ancho)
  ctx.font = `800 ${tam}px "${FUENTE}"`
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillStyle = '#fff'
  ctx.fillText(nombre, 700, 150 + tam * 0.04)
}

function Modelo({ color, giro, nombre = '', tapa = 'pico' }: Termo3DProps) {
  const { scene } = useGLTF(MODELO, false, true)
  const mats = useMemo(() => {
    const canvas = document.createElement('canvas')
    const textura = new THREE.CanvasTexture(canvas)
    textura.flipY = false
    textura.colorSpace = THREE.SRGBColorSpace
    textura.anisotropy = 8
    return {
      canvas,
      textura,
      pintura: new THREE.MeshPhysicalMaterial({ roughness: 0.48, clearcoat: 0.2, clearcoatRoughness: 0.35 }),
      acero: new THREE.MeshStandardMaterial({ color: '#d4d8dc', metalness: 1, roughness: 0.22 }),
      grabado: new THREE.MeshStandardMaterial({ color: '#c9ced3', metalness: 1, roughness: 0.42 }),
      goma: new THREE.MeshStandardMaterial({ color: '#1c1c1e', roughness: 0.82 }),
      nombre: new THREE.MeshStandardMaterial({ color: '#dfe3e6', metalness: 1, roughness: 0.38, map: textura, alphaTest: 0.5 }),
    }
  }, [])

  useLayoutEffect(() => {
    scene.traverse((o) => {
      if (!(o instanceof THREE.Mesh)) return
      o.userData.material ??= (o.material as THREE.Material).name
      const n = o.userData.material as string
      o.material = n === 'Pintura' ? mats.pintura : n === 'Grabado' ? mats.grabado : n === 'Goma' ? mats.goma : n === 'Nombre' ? mats.nombre : mats.acero
    })
    for (const p of ['Cuerpo', 'Manija', 'Logo', 'Nombre']) {
      const a = scene.getObjectByName(`${p}_1L`)
      const b = scene.getObjectByName(`${p}_15L`)
      if (a) a.visible = true
      if (b) b.visible = false
    }
    for (const [id, nodo] of [['clasica', 'Tapa_Clasica'], ['pico', 'Tapa_Pico'], ['mate', 'Tapa_Mate']] as const) {
      const o = scene.getObjectByName(nodo)
      if (o) o.visible = tapa === id
    }
  }, [scene, mats, tapa])

  useLayoutEffect(() => {
    mats.pintura.color.set(color)
  }, [color, mats])

  useLayoutEffect(() => {
    dibujar(mats.canvas, nombre)
    mats.textura.needsUpdate = true
  }, [nombre, mats])

  return <primitive object={scene} rotation={[0, THREE.MathUtils.degToRad(giro), 0]} />
}

function Camara({ camara }: Pick<Termo3DProps, 'camara'>) {
  const cam = useThree((s) => s.camera)
  useLayoutEffect(() => {
    cam.position.set(0, camara.altura, camara.distancia)
    cam.lookAt(0, camara.objetivo, 0)
    cam.updateProjectionMatrix()
  }, [cam, camara.altura, camara.distancia, camara.objetivo])
  return null
}

/** El termo del GLB de Blender, con luz de estudio armada con paneles (nada se anima solo: todo sale de las props). */
export function Termo3D(props: Termo3DProps) {
  const contraluz = props.luz === 'contraluz'
  return (
    <>
      <Camara camara={props.camara} />
      <Modelo {...props} />
      <Environment resolution={256} frames={1}>
        {contraluz ? (
          <>
            <Lightformer form="rect" intensity={7} position={[-0.9, 0.4, -1.2]} scale={[0.25, 3, 1]} rotation-y={Math.PI / 5} />
            <Lightformer form="rect" intensity={7} position={[0.9, 0.4, -1.2]} scale={[0.25, 3, 1]} rotation-y={-Math.PI / 5} />
            <Lightformer form="rect" intensity={0.15} position={[0, 0.2, 1.5]} scale={[3, 1, 1]} />
          </>
        ) : (
          <>
            <Lightformer form="rect" intensity={2.2} position={[0, 1.2, 0.4]} scale={[2, 1, 1]} rotation-x={Math.PI / 2} />
            <Lightformer form="rect" intensity={3} position={[-1.1, 0.3, 0.6]} scale={[0.5, 2.2, 1]} rotation-y={Math.PI / 2.6} />
            <Lightformer form="rect" intensity={1.6} position={[1.2, 0.3, -0.4]} scale={[0.35, 2, 1]} rotation-y={-Math.PI / 2} />
            <Lightformer form="rect" intensity={0.6} position={[0, -0.4, 1]} scale={[3, 0.6, 1]} />
          </>
        )}
      </Environment>
    </>
  )
}

useGLTF.preload(MODELO, false, true)
