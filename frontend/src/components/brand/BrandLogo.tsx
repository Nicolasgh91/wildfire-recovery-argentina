import { Trees } from 'lucide-react'
import { useState } from 'react'
import { BRAND } from '@/config/brand'
import { useTheme } from 'next-themes'
import { cn } from '@/lib/utils'

interface BrandLogoProps {
  size?: 'sm' | 'md' | 'lg'
  className?: string
  showName?: boolean
  nameClassName?: string
}

const sizeMap = {
  sm: { icon: 'h-6 w-6', text: 'text-base font-bold', img: 'h-6' },
  md: { icon: 'h-8 w-8', text: 'text-xl font-bold', img: 'h-8' },
  lg: { icon: 'h-10 w-10', text: 'text-2xl font-bold', img: 'h-10' },
}

export function BrandLogo({ size = 'md', className, showName = true, nameClassName }: BrandLogoProps) {
  const { resolvedTheme } = useTheme()
  const [imgError, setImgError] = useState(false)
  const sizes = sizeMap[size]

  const logoSrc = resolvedTheme === 'dark' ? BRAND.logos.dark : BRAND.logos.light

  return (
    <span className={cn('flex items-center gap-2', className)}>
      {!imgError ? (
        <img
          src={logoSrc}
          alt={BRAND.name}
          className={cn(sizes.img, 'object-contain')}
          onError={() => setImgError(true)}
        />
      ) : (
        <Trees className={cn(sizes.icon, 'text-primary')} />
      )}
      {showName && (
        <span className={cn(sizes.text, 'text-foreground', nameClassName)}>
          {BRAND.name}
        </span>
      )}
    </span>
  )
}
