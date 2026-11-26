import { expect, test, type Page } from '@playwright/test'
import { mkdirSync, writeFileSync } from 'node:fs'

const COLOR = { id: 'siesta', base: '#ea5a1c' }
const NOMBRE = 'Rocío'

type Apertura = { href: string; rel: string | null; download: string | null; ms: number }
type Ventana = { __ar: Apertura[]; __toque: number }

/**
 * Lo que un navegador emulado no trae y un celular real sí:
 * - Safari de iPhone anuncia AR Quick Look con `<a rel="ar">` (relList.supports('ar')).
 * - Abrir AR es hacer clic en un enlace oculto (Quick Look o el intent de Scene Viewer): lo
 *   anotamos en vez de navegar, para revisar a dónde iba y qué archivo llevaba.
 * - En un celular real, sacar `revokeObjectURL` no cambia nada: Quick Look ya recibió el archivo.
 */
async function prepararDispositivo(page: Page, ios: boolean) {
  await page.addInitScript((ios) => {
    if (ios) {
      const original = DOMTokenList.prototype.supports
      DOMTokenList.prototype.supports = function (token: string) {
        return token === 'ar' ? true : original.call(this, token)
      }
    }
    // model-viewer libera el USDZ apenas lo entrega a Quick Look: lo guardamos para revisarlo
    URL.revokeObjectURL = () => {}
    const w = window as unknown as Ventana
    w.__ar = []
    w.__toque = 0
    document.addEventListener('click', () => (w.__toque = performance.now()), true)
    const clic = HTMLAnchorElement.prototype.click
    HTMLAnchorElement.prototype.click = function () {
      if (this.rel === 'ar' || this.href.startsWith('intent:')) {
        w.__ar.push({
          href: this.href,
          rel: this.getAttribute('rel'),
          download: this.getAttribute('download'),
          ms: performance.now() - w.__toque,
        })
        return
      }
      return clic.call(this)
    }
  }, ios)
}

async function abrirMesa(page: Page) {
  await page.goto(`/?color=${COLOR.id}&nombre=${encodeURIComponent(NOMBRE)}#hacelo`)
  await page.getByRole('button', { name: 'Ver en tu mesa' }).click()
  const dialogo = page.getByRole('dialog', { name: 'Ver en tu mesa' })
  await expect(dialogo).toBeVisible({ timeout: 20_000 })
  return dialogo
}

const primeraApertura = (page: Page) =>
  page
    .waitForFunction(() => (window as unknown as Ventana).__ar.length > 0, null, { timeout: 30_000 })
    .then(() => page.evaluate(() => (window as unknown as Ventana).__ar[0]))

/** Lee un .usdz (un zip sin comprimir) y devuelve sus archivos. */
function leerZip(buf: Buffer) {
  const archivos = new Map<string, Buffer>()
  let i = 0
  while (i + 4 <= buf.length && buf.readUInt32LE(i) === 0x04034b50) {
    const metodo = buf.readUInt16LE(i + 8)
    const tam = buf.readUInt32LE(i + 18)
    const largoNombre = buf.readUInt16LE(i + 26)
    const largoExtra = buf.readUInt16LE(i + 28)
    const nombre = buf.toString('utf8', i + 30, i + 30 + largoNombre)
    const inicio = i + 30 + largoNombre + largoExtra
    expect(metodo, `${nombre} va sin comprimir, como pide USDZ`).toBe(0)
    archivos.set(nombre, buf.subarray(inicio, inicio + tam))
    i = inicio + tam
  }
  return archivos
}

const lineal = (c: number) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4)

test('iPhone: ofrece AR y abre Quick Look con un USDZ del termo con su color y su nombre', async ({ page }, info) => {
  test.skip(info.project.name !== 'iphone')
  await prepararDispositivo(page, true)
  const dialogo = await abrirMesa(page)

  await expect(dialogo.getByText('Apuntá la cámara a una mesa')).toBeVisible({ timeout: 20_000 })
  await expect(dialogo.getByText('Desde la computadora no se puede usar la cámara')).toHaveCount(0)

  // Que cargue el modelo con el color y el nombre aplicados antes de tocar el botón
  await page.waitForFunction(() => (document.querySelector('model-viewer') as unknown as { loaded?: boolean } | null)?.loaded)
  await page.waitForTimeout(800)
  await dialogo.getByRole('button', { name: 'Ponerlo sobre la mesa' }).click()
  const ar = await primeraApertura(page)

  expect(ar.rel).toBe('ar')
  expect(ar.href).toMatch(/^blob:/)
  expect(ar.href).toContain('allowsContentScaling=0') // tamaño real: no se puede agrandar pellizcando
  info.annotations.push({ type: 'armado del USDZ', description: `${Math.round(ar.ms)} ms desde el toque` })

  const bytes = await page.evaluate(async (url) => {
    const r = await fetch(url.split('#')[0])
    return Array.from(new Uint8Array(await r.arrayBuffer()))
  }, ar.href)
  const usdz = leerZip(Buffer.from(bytes))
  const usda = [...usdz].find(([n]) => n.endsWith('.usda'))
  expect(usda, 'el USDZ trae la escena').toBeTruthy()
  const texto = usda![1].toString('utf8')
  mkdirSync('test-results/usdz', { recursive: true })
  writeFileSync('test-results/usdz/kuarahy.usdz', Buffer.from(bytes))
  writeFileSync('test-results/usdz/escena.usda', texto)

  // Color: la pintura sale con el color elegido (el exportador escribe el color lineal)
  const esperado = [1, 3, 5].map((k) => lineal(parseInt(COLOR.base.slice(k, k + 2), 16) / 255))
  const colores = [...texto.matchAll(/\(([\d.]+), ([\d.]+), ([\d.]+)\)/g)].map((m) => [m[1], m[2], m[3]].map(Number))
  expect(
    colores.some((c) => c.every((v, k) => Math.abs(v - esperado[k]) < 0.01)),
    `el color ${COLOR.base} está en el USDZ`,
  ).toBe(true)

  // Nombre: la pieza "Nombre_…" usa un material con textura, y esa textura viaja dentro del USDZ
  // (el exportador numera los materiales, así que se sigue el vínculo desde la pieza)
  const material = texto.match(/def Xform "Nombre_[^"]*"[\s\S]*?rel material:binding = <\/Materials\/([^>]+)>/)?.[1]
  expect(material, 'la pieza del nombre está en el USDZ').toBeTruthy()
  const bloque = texto.slice(texto.indexOf(`def Material "${material}"`))
  const fin = bloque.indexOf('def Material', 10)
  const textura = bloque.slice(0, fin < 0 ? undefined : fin).match(/@(textures\/[^@]+)@/)?.[1]
  expect(textura, 'el material del nombre tiene textura').toBeTruthy()
  const png = usdz.get(textura!)
  expect(png && png.length > 1000, 'la textura del nombre está en el USDZ').toBe(true)
  writeFileSync(`test-results/usdz/${textura!.split('/').pop()}`, png!)
})

test('Android: ofrece AR y abre Scene Viewer con el modelo a tamaño real', async ({ page }, info) => {
  test.skip(info.project.name !== 'android')
  await prepararDispositivo(page, false)
  const dialogo = await abrirMesa(page)
  await expect(dialogo.getByText('Apuntá la cámara a una mesa')).toBeVisible({ timeout: 20_000 })
  await expect(dialogo.getByText('Desde la computadora no se puede usar la cámara')).toHaveCount(0)

  await dialogo.getByRole('button', { name: 'Ponerlo sobre la mesa' }).click()
  const ar = await primeraApertura(page)
  expect(ar.href).toMatch(/^intent:\/\/arvr\.google\.com\/scene-viewer/)
  expect(ar.href).toContain('kuarahy-1L-pico.glb')
  expect(ar.href).toContain('resizable=false')
})

test('Computadora: no ofrece AR y muestra el QR con el mismo diseño', async ({ page }, info) => {
  test.skip(info.project.name !== 'escritorio')
  await prepararDispositivo(page, false)
  const dialogo = await abrirMesa(page)
  await expect(dialogo.getByText('Desde la computadora no se puede usar la cámara')).toBeVisible({ timeout: 20_000 })
  await expect(dialogo.getByRole('img', { name: 'Código QR con este mismo diseño' })).toBeVisible()
  await expect(dialogo.getByText('Apuntá la cámara a una mesa')).toHaveCount(0)
})
