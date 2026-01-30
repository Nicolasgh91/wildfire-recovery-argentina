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
  selectedStatus: string
  onProvinceChange: (value: string) => void
  onStatusChange: (value: string) => void
}

export function FireFilters({
  selectedProvince,
  selectedStatus,
  onProvinceChange,
  onStatusChange,
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

      <Select value={selectedStatus} onValueChange={onStatusChange}>
        <SelectTrigger className="w-[180px]">
          <SelectValue placeholder={t('status')} />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">{t('all')}</SelectItem>
          <SelectItem value="active">{t('active')}</SelectItem>
          <SelectItem value="extinguished">{t('extinguished')}</SelectItem>
        </SelectContent>
      </Select>
    </div>
  )
}
