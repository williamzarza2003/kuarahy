import { loadFont } from '@remotion/fonts'
import { staticFile } from 'remotion'

// Los mismos colores y la misma tipografía de la web (src/index.css y src/data/variantes.ts)
export const COLOR = {
  sol: '#ff5f1f',
  solOscuro: '#c63d06',
  solClaro: '#ffb24a',
  hielo: '#b9f1fd',
  noche: '#0b1820',
  noche2: '#142733',
  tinta: '#11161a',
}

export const VARIANTES = [
  { id: 'lapacho', nombre: 'Lapacho', base: '#e0518d', fondo: '#fbd3e4' },
  { id: 'siesta', nombre: 'Siesta', base: '#ea5a1c', fondo: '#ffd9c2' },
  { id: 'parana', nombre: 'Paraná', base: '#1d6ea3', fondo: '#cfe8f7' },
  { id: 'monte', nombre: 'Monte', base: '#2d7451', fondo: '#d3ecdd' },
  { id: 'carbon', nombre: 'Carbón', base: '#2a2d33', fondo: '#e3e5e8' },
] as const

export const FUENTE = 'Bricolage Grotesque'

// Carga una sola vez, antes de renderizar cualquier cuadro (el grabado del canvas la necesita)
export const fuentesListas = Promise.all([
  loadFont({ family: FUENTE, url: staticFile('fuentes/Bricolage-ExtraBold.woff2'), weight: '800' }),
  loadFont({ family: FUENTE, url: staticFile('fuentes/Bricolage-SemiBold.woff2'), weight: '600' }),
])
