import type { TranslationKey } from '@/types/translation-keys'

export type PublicSourceLink = {
  labelKey: TranslationKey
  href: string
  tooltipKey: TranslationKey
}

export type PublicSourceItem = PublicSourceLink | readonly PublicSourceLink[]

export const PUBLIC_SOURCES_AR: readonly PublicSourceItem[] = [
  {
    labelKey: 'footerExternalSnmfLabel',
    href: 'https://www.argentina.gob.ar/servicio-nacional-de-manejo-del-fuego',
    tooltipKey: 'footerExternalSnmfTooltip',
  },
  [
    {
      labelKey: 'footerExternalBoletinLabel',
      href: 'https://www.boletinoficial.gob.ar/',
      tooltipKey: 'footerExternalBoletinTooltip',
    },
    {
      labelKey: 'footerExternalConaeLabel',
      href: 'https://catalogos5.conae.gov.ar/catalogofocos/',
      tooltipKey: 'footerExternalConaeTooltip',
    },
  ],
  {
    labelKey: 'footerExternalSmnLabel',
    href: 'https://ws2.smn.gob.ar/',
    tooltipKey: 'footerExternalSmnTooltip',
  },
  [
    {
      labelKey: 'footerExternalSpmfLabel',
      href: 'https://bosques.chubut.gov.ar/manejo-del-fuego/',
      tooltipKey: 'footerExternalSpmfTooltip',
    },
    {
      labelKey: 'footerExternalSplifLabel',
      href: 'https://splif.rionegro.gov.ar/',
      tooltipKey: 'footerExternalSplifTooltip',
    },
  ],
] as const
