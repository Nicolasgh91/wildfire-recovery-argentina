/**
 * AnimatedGradientText - Componente de animación de texto con gradiente
 *
 * Comportamiento:
 * - Revela el texto de izquierda a derecha con efecto de gradiente
 * - Respeta prefers-reduced-motion (muestra texto estático)
 * - Usa GPU acceleration para animación fluida
 *
 * @example
 * <AnimatedGradientText
 *   text="Título principal"
 *   as="h1"
 *   duration={1.2}
 *   delay={0.3}
 * />
 */

import { motion, useReducedMotion } from 'framer-motion'
import { ElementType, ComponentPropsWithoutRef } from 'react'
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
  const shouldReduceMotion = useReducedMotion()
  const Component = as || 'span'

  // Fallback para navegadores sin soporte de background-clip: text
  const supportsBackgroundClipText =
    typeof CSS !== 'undefined' && CSS.supports('background-clip', 'text')

  if (shouldReduceMotion || !supportsBackgroundClipText) {
    return (
      <Component className={cn('text-gray-900', className)} {...props}>
        {text}
      </Component>
    )
  }

  return (
    <motion.span
      className={cn(
        'inline-block bg-clip-text text-transparent',
        'will-change-[background-position]', // GPU acceleration
        className
      )}
      style={{
        backgroundImage: `linear-gradient(90deg, ${toColor} 0%, ${toColor} 50%, ${fromColor} 50%, ${fromColor} 100%)`,
        backgroundSize: '200% 100%',
        backgroundPosition: '100% 0',
      }}
      initial={{ backgroundPosition: '100% 0' }}
      animate={{ backgroundPosition: '0% 0' }}
      transition={{
        duration,
        delay,
        ease: [0.25, 0.46, 0.45, 0.94], // easeOutQuad
      }}
      aria-label={text}
      {...props}
    >
      {text}
    </motion.span>
  )
}
