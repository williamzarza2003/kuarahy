import { variantes, type Variante } from './variantes.ts'

/** Tamaños del termo. El modelo 3D trae los dos cuerpos y la web muestra uno. */
export const tamanos = [
  { id: '1L', nombre: '1 L', detalle: 'Una ronda para tres o cuatro', precio: 289_000 },
  { id: '15L', nombre: '1,5 L', detalle: 'La ronda larga de la siesta', precio: 339_000 },
] as const

export const tapas = [
  { id: 'clasica', nombre: 'Clásica', detalle: 'Con asa plegable de acero', precio: 0 },
  { id: 'pico', nombre: 'Pico cebador', detalle: 'Sirve de a poco, con una mano', precio: 25_000 },
] as const

export const PRECIO_GRABADO = 30_000
export const MAX_NOMBRE = 14

export type TamanoId = (typeof tamanos)[number]['id']
export type TapaId = (typeof tapas)[number]['id']

export interface Configuracion {
  color: Variante['id']
  nombre: string
  tapa: TapaId
  tamano: TamanoId
}

export const INICIAL: Configuracion = { color: 'lapacho', nombre: '', tapa: 'clasica', tamano: '1L' }

/** Deja solo letras (con acentos y ñ), números, espacios, punto y guion; máximo 14 caracteres. */
export function limpiarNombre(texto: string): string {
  return texto
    .replace(/[^\p{L}\p{N} .'-]/gu, '')
    .replace(/\s{2,}/g, ' ')
    .trimStart()
    .slice(0, MAX_NOMBRE)
}

export function precio(c: Configuracion): number {
  const t = tamanos.find((x) => x.id === c.tamano)!
  const tp = tapas.find((x) => x.id === c.tapa)!
  return t.precio + tp.precio + (c.nombre.trim() ? PRECIO_GRABADO : 0)
}

export const guaranies = (n: number) => '₲ ' + n.toLocaleString('es-PY')

/** Lee el diseño de la URL (?color=parana&nombre=Ana&tapa=pico&tamano=15L), ignorando valores inválidos. */
export function desdeURL(busqueda: string): Configuracion {
  const p = new URLSearchParams(busqueda)
  const color = variantes.some((v) => v.id === p.get('color')) ? (p.get('color') as Variante['id']) : INICIAL.color
  const tapa = tapas.some((t) => t.id === p.get('tapa')) ? (p.get('tapa') as TapaId) : INICIAL.tapa
  const tamano = tamanos.some((t) => t.id === p.get('tamano')) ? (p.get('tamano') as TamanoId) : INICIAL.tamano
  return { color, tapa, tamano, nombre: limpiarNombre(p.get('nombre') ?? '') }
}

/** Solo guarda lo que difiere del diseño inicial, para que el enlace sea corto. */
export function aURL(c: Configuracion): string {
  const p = new URLSearchParams()
  if (c.color !== INICIAL.color) p.set('color', c.color)
  if (c.nombre.trim()) p.set('nombre', c.nombre.trim())
  if (c.tapa !== INICIAL.tapa) p.set('tapa', c.tapa)
  if (c.tamano !== INICIAL.tamano) p.set('tamano', c.tamano)
  const q = p.toString()
  return q ? `?${q}` : ''
}

export const varianteDe = (id: Variante['id']) => variantes.find((v) => v.id === id) ?? variantes[0]
