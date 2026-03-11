import { describe, expect, it } from 'vitest'
import { render } from '@testing-library/react'
import { SEOHead } from './SEOHead'

describe('SEOHead', () => {
  it('renderiza título con sufijo ForestGuard', () => {
    render(<SEOHead title="Córdoba" description="Desc" />)
    expect(document.title).toBe('Córdoba | ForestGuard')
  })

  it('renderiza rel=prev y rel=next cuando se pasan', () => {
    render(
      <SEOHead
        title="Córdoba p2"
        description="Desc"
        prevPage="https://forestguard.com.ar/provincias/cordoba"
        nextPage="https://forestguard.com.ar/provincias/cordoba/pagina/3"
      />,
    )

    const prev = document.querySelector<HTMLLinkElement>('link[rel="prev"]')
    const next = document.querySelector<HTMLLinkElement>('link[rel="next"]')

    expect(prev?.href).toBe('https://forestguard.com.ar/provincias/cordoba')
    expect(next?.href).toBe('https://forestguard.com.ar/provincias/cordoba/pagina/3')
  })

  it('no renderiza rel=prev ni rel=next si no se pasan', () => {
    render(<SEOHead title="T" description="D" />)
    expect(document.querySelector('link[rel="prev"]')).toBeNull()
    expect(document.querySelector('link[rel="next"]')).toBeNull()
  })

  it('acepta jsonld como array y genera un <script> por bloque', () => {
    const blocks = [{ '@type': 'Dataset' }, { '@type': 'CollectionPage' }]
    render(<SEOHead title="T" description="D" jsonld={blocks} />)
    const scripts = document.querySelectorAll('script[type="application/ld+json"]')
    expect(scripts.length).toBe(2)
  })

  it('no renderiza og:image si ogImage es null o undefined', () => {
    render(<SEOHead title="T" description="D" ogImage={null} />)
    expect(document.querySelector('meta[property="og:image"]')).toBeNull()
  })

  it('no emite meta robots por defecto', () => {
    render(<SEOHead title="T" description="D" />)
    expect(document.querySelector('meta[name="robots"]')).toBeNull()
  })

  it('emite meta robots noindex cuando se indica', () => {
    render(<SEOHead title="T" description="D" noindex />)
    const robots = document.querySelector<HTMLMetaElement>('meta[name="robots"]')
    expect(robots?.content).toBe('noindex')
  })
})

