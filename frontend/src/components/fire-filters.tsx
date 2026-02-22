import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useI18n } from '@/context/LanguageContext'
import { provinces } from '@/data/mockdata'

interface FireFiltersProps {
  selectedProvince: string
  onProvinceChange: (value: string) => void
}

export function FireFilters({
  selectedProvince,
  onProvinceChange,
}: FireFiltersProps) {
  const { t } = useI18n()

  return (
    <div className="flex flex-wrap gap-3">
      <Select value={selectedProvince} onValueChange={onProvinceChange}>
        <SelectTrigger className="w-[180px]">
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
    </div>
  )
}
