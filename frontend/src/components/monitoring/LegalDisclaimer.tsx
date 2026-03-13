const DEFAULT_DISCLAIMER =
  'Los resultados presentados constituyen alertas generadas mediante ' +
  'detección remota satelital (Sentinel-2) y análisis automatizado de ' +
  'índices de vegetación. No reemplazan la verificación técnica y legal ' +
  'presencial. Su interpretación requiere validación por profesionales ' +
  'habilitados conforme a la ley 26.815 y su modificatoria 27.604.'

interface LegalDisclaimerProps {
  text?: string | null
}

export function LegalDisclaimer({ text }: LegalDisclaimerProps) {
  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 dark:border-amber-900 dark:bg-amber-950">
      <p className="text-xs text-amber-800 dark:text-amber-200">
        {text ?? DEFAULT_DISCLAIMER}
      </p>
    </div>
  )
}
