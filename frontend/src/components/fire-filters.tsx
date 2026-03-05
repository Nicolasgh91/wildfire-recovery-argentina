import { ArrowDown, ArrowUp, Flame, Maximize2 } from 'lucide-react'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { useI18n } from '@/context/LanguageContext'
import { provinces } from '@/data/mockdata'
import { cn } from '@/lib/utils'

const PILL_BASE =
  'h-8 rounded-full text-sm font-medium shrink-0 transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2'

interface FireFiltersProps {
  selectedProvince: string
  onProvinceChange: (value: string) => void
  sortOrder: 'asc' | 'desc'
  onSortOrderChange: (value: 'asc' | 'desc') => void
  soloActivos: boolean
  onSoloActivosChange: (value: boolean) => void
  grandesFocos: boolean
  onGrandesFocosChange: (value: boolean) => void
}

export function FireFilters({
  selectedProvince,
  onProvinceChange,
  sortOrder,
  onSortOrderChange,
  soloActivos,
  onSoloActivosChange,
  grandesFocos,
  onGrandesFocosChange,
}: FireFiltersProps) {
  const { t } = useI18n()
  const provinceActive = selectedProvince !== 'all'

  return (
    <div className="flex w-full flex-nowrap items-center gap-2 overflow-x-auto pb-2 scrollbar-hide">
      <Select value={selectedProvince} onValueChange={onProvinceChange}>
        <SelectTrigger
          size="sm"
          className={cn(
            PILL_BASE,
            'min-w-0 w-auto px-4 border',
            provinceActive
              ? 'bg-secondary text-secondary-foreground border-secondary'
              : 'bg-muted/50 border-border hover:bg-muted/70'
          )}
        >
          <SelectValue placeholder={t('province')} />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">{t('all')}</SelectItem>
          {provinces.map((province) => (
            <SelectItem key={province} value={province}>
              {province}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={() => onSortOrderChange(sortOrder === 'desc' ? 'asc' : 'desc')}
        title={sortOrder === 'desc' ? t('sortNewestFirst') : t('sortOldestFirst')}
        className={cn(
          PILL_BASE,
          'gap-1.5 px-4 border bg-muted/50 border-border hover:bg-muted/70'
        )}
      >
        {sortOrder === 'desc' ? (
          <ArrowDown className="h-4 w-4 shrink-0" />
        ) : (
          <ArrowUp className="h-4 w-4 shrink-0" />
        )}
        {t('sortByDate')}
      </Button>

      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={() => onSoloActivosChange(!soloActivos)}
        className={cn(
          PILL_BASE,
          'gap-1.5 px-4 border',
          soloActivos
            ? 'bg-secondary text-secondary-foreground border-secondary'
            : 'bg-muted/50 border-border hover:bg-muted/70'
        )}
      >
        <Flame className="h-4 w-4 shrink-0" />
        Solo activos
      </Button>

      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={() => onGrandesFocosChange(!grandesFocos)}
        className={cn(
          PILL_BASE,
          'gap-1.5 px-4 border',
          grandesFocos
            ? 'bg-secondary text-secondary-foreground border-secondary'
            : 'bg-muted/50 border-border hover:bg-muted/70'
        )}
      >
        <Maximize2 className="h-4 w-4 shrink-0" />
        Grandes focos
      </Button>
    </div>
  )
}
