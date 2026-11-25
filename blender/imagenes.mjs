// Kuarahy · renders de Blender (PNG) → AVIF + WebP para la web, en 640, 1200 y 1920 px de ancho.
// Uso: node blender/imagenes.mjs   (después de blender/render.py --calidad final)
import { readdir, mkdir, stat } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import sharp from 'sharp'

const aqui = path.dirname(fileURLToPath(import.meta.url))
const origen = path.join(aqui, 'renders')
const destino = path.join(aqui, '..', 'public', 'img', 'renders')
await mkdir(destino, { recursive: true })

const anchos = [640, 1200, 1920]
let total = 0
for (const archivo of (await readdir(origen)).filter((f) => f.endsWith('.png') && !f.includes('-boceto'))) {
  const base = archivo.replace(/\.png$/, '')
  let img = sharp(path.join(origen, archivo))
  const { width, height } = await img.metadata()
  if (base.startsWith('estudio-')) {
    // Fondo transparente: la sombra de contacto se desvanece en óvalo hacia los bordes,
    // así no queda cortada en un rectángulo cuando la foto va sobre un color plano.
    // Con el encuadre v3 la base del termo queda al 89 % del alto: la sombra se borra entre el 90 % y el
    // borde de abajo (si no, termina en una línea recta), y un óvalo la apaga hacia los costados.
    const mascara = Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}">
      <defs>
        <radialGradient id="g" cx="50%" cy="50%" r="62%">
          <stop offset="64%" stop-color="#fff" stop-opacity="1"/><stop offset="100%" stop-color="#fff" stop-opacity="0"/>
        </radialGradient>
        <linearGradient id="v" x1="0" y1="0" x2="0" y2="1">
          <stop offset="90%" stop-color="#fff" stop-opacity="1"/><stop offset="99%" stop-color="#fff" stop-opacity="0"/>
        </linearGradient>
        <mask id="m"><rect width="100%" height="100%" fill="url(#v)"/></mask>
      </defs><rect width="100%" height="100%" fill="url(#g)" mask="url(#m)"/></svg>`)
    img = sharp(await img.composite([{ input: mascara, blend: 'dest-in' }]).png().toBuffer())
  }
  for (const ancho of anchos.filter((a) => a <= width || a === 640)) {
    const r = img.clone().resize({ width: Math.min(ancho, width) })
    await r.clone().webp({ quality: 82, alphaQuality: 90, effort: 5 }).toFile(path.join(destino, `${base}-${ancho}.webp`))
    await r.clone().avif({ quality: 58, effort: 5 }).toFile(path.join(destino, `${base}-${ancho}.avif`))
  }
  const kb = (await stat(path.join(destino, `${base}-1200.avif`)).catch(() => ({ size: 0 }))).size / 1024
  total++
  console.log(`${base}: ${width}px → AVIF 1200 ${kb.toFixed(0)} KB`)
}
console.log(`${total} renders listos en public/img/renders`)
