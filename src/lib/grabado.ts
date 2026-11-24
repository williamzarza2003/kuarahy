/**
 * Dibuja el nombre grabado en un canvas transparente. Lo usan el visor 3D (CanvasTexture)
 * y la realidad aumentada (<model-viewer> createTexture), así el grabado es el mismo en los dos.
 *
 * La banda del modelo cubre 80° del cuerpo (≈ 7 cm × 1,5 cm): el canvas respeta esa proporción.
 */
export const ANCHO_GRABADO = 1400
export const ALTO_GRABADO = 300
const FUENTE = '"Bricolage Grotesque", "Arial Black", sans-serif'

export async function fuenteLista() {
  try {
    await document.fonts.load(`800 120px ${FUENTE}`)
  } catch {
    // si la fuente no carga se usa la de respaldo: el grabado sale igual
  }
}

/**
 * @param fondo  color de fondo opaco (la realidad aumentada no respeta el alfa de una textura creada en vivo:
 *               ahí la banda se pinta del color del termo y el nombre en gris acero)
 */
export function dibujarGrabado(canvas: HTMLCanvasElement, nombre: string, fondo?: string) {
  canvas.width = ANCHO_GRABADO
  canvas.height = ALTO_GRABADO
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.clearRect(0, 0, ANCHO_GRABADO, ALTO_GRABADO)
  if (fondo) {
    ctx.fillStyle = fondo
    ctx.fillRect(0, 0, ANCHO_GRABADO, ALTO_GRABADO)
  }
  const texto = nombre.trim()
  if (!texto) return
  // Tamaño que entra a lo ancho, con tope de alto: los nombres cortos no quedan gigantes
  let tam = 230
  ctx.font = `800 ${tam}px ${FUENTE}`
  const ancho = ctx.measureText(texto).width
  const maximo = ANCHO_GRABADO * 0.86
  if (ancho > maximo) tam = Math.floor((tam * maximo) / ancho)
  ctx.font = `800 ${tam}px ${FUENTE}`
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillStyle = fondo ? '#d9dde0' : '#ffffff'
  ctx.fillText(texto, ANCHO_GRABADO / 2, ALTO_GRABADO / 2 + tam * 0.04)
}
