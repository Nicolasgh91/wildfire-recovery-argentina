/**
 * AnimatedGradientText - Componente de animación de texto con gradiente
 *
 * Comportamiento:
 * - Revela el texto de izquierda a derecha con efecto de gradiente
 * - Respeta prefers-reduced-motion (muestra texto estático)
 * - Usa GPU acceleration para animación fluida
 * - Implementado con CSS puro (sin dependencias de librerías de animación)
 *
 * @example
 * <AnimatedGradientText
 *   text="Título principal"
 *   as="h1"
 *   duration={1.2}
 *   delay={0.3}
 * />
 */

import { useEffect, useState, type ElementType, type ComponentPropsWithoutRef } from 'react'
import { cn } from '@/lib/utils'

interface AnimatedGradientTextProps<T extends ElementType = 'span'> {
  text: string
  as?: T
  delay?: number
  duration?: number
  className?: string
  /** Color inicial (gris suave) */
  fromColor?: string
  /** Color final (gris carbón) */
  toColor?: string
}

export function AnimatedGradientText<T extends ElementType = 'span'>({
  text,
  as,
  delay = 0,
  duration = 1.2,
  className,
  fromColor = '#9ca3af', // gray-400
  toColor = '#111827', // gray-900
  ...props
}: AnimatedGradientTextProps<T> &
  Omit<ComponentPropsWithoutRef<T>, keyof AnimatedGradientTextProps<T>>) {
  const Component = as || 'span'
  const [shouldAnimate, setShouldAnimate] = useState(false)

  useEffect(() => {
    // Respetar prefers-reduced-motion
    if (typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      return
    }
    // Verificar soporte de background-clip: text
    if (typeof CSS !== 'undefined' && !CSS.supports('background-clip', 'text')) {
      return
    }
    // Iniciar animación después del delay
    const timer = setTimeout(() => setShouldAnimate(true), delay * 1000)
    return () => clearTimeout(timer)
  }, [delay])

  // Fallback estático para reduced-motion o sin soporte
  const supportsBackgroundClipText =
    typeof CSS !== 'undefined' && CSS.supports('background-clip', 'text')
  const prefersReducedMotion =
    typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches

  if (prefersReducedMotion || !supportsBackgroundClipText) {
    return (
      <Component className={cn('text-gray-900', className)} {...props}>
        {text}
      </Component>
    )
  }

  return (
    <span
      className={cn(
        'inline-block bg-clip-text text-transparent',
        className
      )}
      style={{
        backgroundImage: `linear-gradient(90deg, ${toColor} 0%, ${toColor} 50%, ${fromColor} 50%, ${fromColor} 100%)`,
        backgroundSize: '200% 100%',
        backgroundPosition: shouldAnimate ? '0% 0' : '100% 0',
        transition: `background-position ${duration}s cubic-bezier(0.25, 0.46, 0.45, 0.94)`,
        willChange: shouldAnimate ? 'auto' : 'background-position',
      }}
      aria-label={text}
      {...props}
    >
      {text}
    </span>
  )
}
