import type { ReactNode } from 'react'
import { createPortal } from 'react-dom'

interface SEOHeadProps {
  title: string
  description: string
  canonical?: string
  ogImage?: string | null
  ogImageWidth?: number
  ogImageHeight?: number
  jsonld?: object | object[]
  prevPage?: string
  nextPage?: string
  noindex?: boolean
  children?: ReactNode
}

export function SEOHead({
  title,
  description,
  canonical,
  ogImage,
  ogImageWidth = 1200,
  ogImageHeight = 630,
  jsonld,
  prevPage,
  nextPage,
  noindex = false,
  children,
}: SEOHeadProps) {
  const fullTitle = `${title} | ForestGuard`
  const jsonldBlocks = jsonld ? (Array.isArray(jsonld) ? jsonld : [jsonld]) : []
  const isClient = typeof document !== 'undefined'

  return (
    <>
      {/* React 19 hace hoist automático de title, meta y link al <head> */}
      <title>{fullTitle}</title>
      <meta name="description" content={description} />

      {canonical && <link rel="canonical" href={canonical} />}
      {prevPage && <link rel="prev" href={prevPage} />}
      {nextPage && <link rel="next" href={nextPage} />}

      {noindex && <meta name="robots" content="noindex" />}

      <meta property="og:title" content={title} />
      <meta property="og:description" content={description} />
      <meta property="og:type" content="website" />
      {ogImage && (
        <>
          <meta property="og:image" content={ogImage} />
          <meta property="og:image:width" content={String(ogImageWidth)} />
          <meta property="og:image:height" content={String(ogImageHeight)} />
        </>
      )}

      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:title" content={title} />
      <meta name="twitter:description" content={description} />
      {ogImage && <meta name="twitter:image" content={ogImage} />}

      {jsonldBlocks.map((block, idx) => {
        const script = (
          <script
            key={idx}
            type="application/ld+json"
            dangerouslySetInnerHTML={{ __html: JSON.stringify(block) }}
          />
        )
        return isClient ? createPortal(script, document.head) : script
      })}

      {children}
    </>
  )
}

