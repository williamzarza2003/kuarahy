import { describe, expect, it } from 'vitest'
import { aURL, desdeURL, INICIAL, limpiarNombre, precio } from '../../data/configuracion.ts'

describe('personalizador', () => {
  it('el diseño va y vuelve por la URL', () => {
    const c = { color: 'parana', nombre: 'Ña Rosa', tapa: 'pico', tamano: '15L' } as const
    expect(desdeURL(aURL(c))).toEqual(c)
  })

  it('el diseño inicial deja la URL limpia', () => {
    expect(aURL(INICIAL)).toBe('')
  })

  it('ignora valores inventados en la URL', () => {
    expect(desdeURL('?color=fucsia&tapa=rosca&tamano=3L&nombre=<script>')).toEqual({ ...INICIAL, nombre: 'script' })
  })

  it('el nombre acepta acentos y ñ, y corta en 14 caracteres', () => {
    expect(limpiarNombre('Ñandutí  Benítez Ozuna')).toBe('Ñandutí Benítez'.slice(0, 14))
    expect(limpiarNombre('😀Ana')).toBe('Ana')
  })

  it('el precio cambia con el tamaño, la tapa y el grabado', () => {
    expect(precio(INICIAL)).toBe(289_000)
    expect(precio({ ...INICIAL, tamano: '15L' })).toBe(339_000)
    expect(precio({ ...INICIAL, tapa: 'pico', nombre: 'Ana' })).toBe(289_000 + 25_000 + 30_000)
    expect(precio({ ...INICIAL, nombre: '   ' })).toBe(289_000)
  })
})
