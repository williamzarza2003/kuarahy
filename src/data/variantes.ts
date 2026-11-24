export interface Variante {
  id: string
  nombre: string
  nota: string
  base: string
  sombra: string
  luz: string
  /** Color del sol grabado y del nombre sobre el cuerpo */
  grabado: string
}

// Colores tomados del paisaje paraguayo, no de una paleta genérica
export const variantes: Variante[] = [
  { id: 'lapacho', nombre: 'Lapacho', nota: 'El rosa de los lapachos en flor, en agosto.', base: '#e0518d', sombra: '#8d2152', luz: '#f7a0c5', grabado: '#fff1f6' },
  { id: 'siesta', nombre: 'Siesta', nota: 'El naranja de las tres de la tarde en enero.', base: '#ea5a1c', sombra: '#8f2a06', luz: '#ffa36b', grabado: '#fff3ea' },
  { id: 'parana', nombre: 'Paraná', nota: 'El azul del río visto desde el puente.', base: '#1d6ea3', sombra: '#0b3452', luz: '#6fb7e3', grabado: '#eaf6ff' },
  { id: 'monte', nombre: 'Monte', nota: 'El verde del monte que queda en Alto Paraná.', base: '#2d7451', sombra: '#103a26', luz: '#78c29c', grabado: '#ecfff4' },
  { id: 'carbon', nombre: 'Carbón', nota: 'Negro mate. No muestra la tierra colorada.', base: '#2a2d33', sombra: '#0c0d10', luz: '#5d636d', grabado: '#ffb547' },
]
