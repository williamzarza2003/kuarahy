// Kuarahy · comprime los GLB exportados por Blender y los deja en public/modelos/.
// Uso: node blender/optimizar.mjs
//
// - dedup + weld + simplify suave + quantize + meshopt (EXT_meshopt_compression): menos de 1/5 del peso
// - el material "Nombre" pasa a alphaMode MASK con una textura transparente de 4×4: la web le pinta
//   encima el nombre grabado (CanvasTexture en el visor, createTexture en <model-viewer>).
import { readdir, readFile, mkdir, copyFile, stat } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { NodeIO } from '@gltf-transform/core'
import { EXTMeshoptCompression, ALL_EXTENSIONS } from '@gltf-transform/extensions'
import { dedup, weld, quantize, prune, meshopt, simplify } from '@gltf-transform/functions'
import { MeshoptEncoder, MeshoptSimplifier } from 'meshoptimizer'

const aqui = path.dirname(fileURLToPath(import.meta.url))
const origen = path.join(aqui, 'exports')
const destino = path.join(aqui, '..', 'public', 'modelos')

// PNG transparente de 4×4 (RGBA), para que la banda del nombre arranque invisible
const PNG_VACIO = await readFile(path.join(aqui, 'assets', 'transparente.png'))

await MeshoptEncoder.ready
await MeshoptSimplifier.ready
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.encoder': MeshoptEncoder })
await mkdir(destino, { recursive: true })

for (const archivo of (await readdir(origen)).filter((f) => f.endsWith('.glb'))) {
  const doc = await io.read(path.join(origen, archivo))
  const nombre = doc.getRoot().listMaterials().find((m) => m.getName() === 'Nombre')
  if (nombre) {
    const tex = doc.createTexture('NombreGrabado').setImage(new Uint8Array(PNG_VACIO)).setMimeType('image/png')
    nombre.setBaseColorTexture(tex).setAlphaMode('MASK').setAlphaCutoff(0.5)
  }
  // Los de realidad aumentada (kuarahy-<tamaño>-<tapa>.glb) van sin meshopt: Scene Viewer y Quick Look
  // no lo garantizan y <model-viewer> bajaría el decodificador de otro dominio. Solo se cuantizan.
  const paraAR = archivo !== 'kuarahy.glb'
  await doc.transform(
    dedup(),
    weld(),
    simplify({ simplifier: MeshoptSimplifier, ratio: 0.75, error: 0.0004 }),
    prune(),
    quantize(),
    ...(paraAR ? [] : [meshopt({ encoder: MeshoptEncoder, level: 'medium' })]),
  )
  if (!paraAR) doc.createExtension(EXTMeshoptCompression).setRequired(true)
  const salida = path.join(destino, archivo)
  await io.write(salida, doc)
  const antes = (await stat(path.join(origen, archivo))).size / 1024
  const despues = (await stat(salida)).size / 1024
  console.log(`${archivo}: ${antes.toFixed(0)} KB → ${despues.toFixed(0)} KB`)
}

for (const archivo of (await readdir(origen)).filter((f) => f.endsWith('.usdz'))) {
  await copyFile(path.join(origen, archivo), path.join(destino, archivo))
  console.log(`${archivo}: copiado`)
}
