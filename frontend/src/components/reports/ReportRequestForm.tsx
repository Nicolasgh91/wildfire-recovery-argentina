import { useEffect, useMemo } from 'react'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { FileText, Scale, CalendarRange } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Badge } from '@/components/ui/badge'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import { useI18n } from '@/context/LanguageContext'
import { useReportRequestMutation } from '@/hooks/mutations/useReportRequest'
import { calculateReportCost, DEFAULT_REPORT_IMAGES } from '@/lib/reports'
import type { PendingReportApproval, ReportOutcome, ReportRequestKind } from '@/types/report-ui'
import type { HistoricalReportRequest, JudicialReportRequest } from '@/types/report'

type ReportFormValues = {
  report_type: ReportRequestKind
  fire_event_id: string
  include_climate: boolean
  include_imagery: boolean
  requester_name: string
  case_reference: string
  protected_area_id: string
  protected_area_name: string
  start_date: string
  end_date: string
  max_images: string
  include_monthly_images: boolean
}

interface ReportRequestFormProps {
  creditsBalance: number | null
  onCostChange?: (credits: number) => void
  onPendingApproval: (pending: PendingReportApproval) => void
  onReportCreated: (outcome: ReportOutcome) => void
  onError?: (message: string | null) => void
  onResetStatus?: () => void
}

const isValidDate = (value: string) => !Number.isNaN(Date.parse(value))

export function ReportRequestForm({
  creditsBalance,
  onCostChange,
  onPendingApproval,
  onReportCreated,
  onError,
  onResetStatus,
}: ReportRequestFormProps) {
  const { t } = useI18n()
  const schema = useMemo(
    () =>
      z
        .object({
          report_type: z.enum(['judicial', 'historical']),
          fire_event_id: z.string().trim().optional(),
          include_climate: z.boolean(),
          include_imagery: z.boolean(),
          requester_name: z.string().trim().optional(),
          case_reference: z.string().trim().optional(),
          protected_area_id: z.string().trim().optional(),
          protected_area_name: z.string().trim().optional(),
          start_date: z.string().trim().optional(),
          end_date: z.string().trim().optional(),
          max_images: z.string().trim(),
          include_monthly_images: z.boolean(),
        })
        .superRefine((data, ctx) => {
          if (data.report_type === 'judicial') {
            if (!data.fire_event_id) {
              ctx.addIssue({
                code: z.ZodIssueCode.custom,
                message: t('requiredField'),
                path: ['fire_event_id'],
              })
            }
            return
          }

          if (!data.start_date) {
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              message: t('requiredField'),
              path: ['start_date'],
            })
          } else if (!isValidDate(data.start_date)) {
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              message: t('invalidValue'),
              path: ['start_date'],
            })
          }

          if (!data.end_date) {
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              message: t('requiredField'),
              path: ['end_date'],
            })
          } else if (!isValidDate(data.end_date)) {
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              message: t('invalidValue'),
              path: ['end_date'],
            })
          } else if (
            data.start_date &&
            isValidDate(data.start_date) &&
            new Date(data.end_date) < new Date(data.start_date)
          ) {
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              message: t('reportDateRangeInvalid'),
              path: ['end_date'],
            })
          }

          if (!data.protected_area_id && !data.protected_area_name) {
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              message: t('reportProtectedAreaRequired'),
              path: ['protected_area_name'],
            })
          }

          const maxImages = Number(data.max_images)
          if (Number.isNaN(maxImages)) {
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              message: t('invalidNumber'),
              path: ['max_images'],
            })
          } else if (maxImages < 1 || maxImages > 12) {
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              message: t('reportMaxImagesRange'),
              path: ['max_images'],
            })
          }
        }),
    [t],
  )

  const form = useForm<ReportFormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      report_type: 'judicial',
      fire_event_id: '',
      include_climate: true,
      include_imagery: true,
      requester_name: '',
      case_reference: '',
      protected_area_id: '',
      protected_area_name: '',
      start_date: '',
      end_date: '',
      max_images: String(DEFAULT_REPORT_IMAGES),
      include_monthly_images: true,
    },
    mode: 'onChange',
  })

  const reportMutation = useReportRequestMutation()
  const reportType = form.watch('report_type')
  const includeImagery = form.watch('include_imagery')
  const maxImagesValue = form.watch('max_images')

  const estimatedCredits = useMemo(() => {
    if (reportType === 'judicial') {
      return calculateReportCost(includeImagery ? DEFAULT_REPORT_IMAGES : 0)
    }
    return calculateReportCost(Number(maxImagesValue))
  }, [includeImagery, maxImagesValue, reportType])

  useEffect(() => {
    onCostChange?.(estimatedCredits)
  }, [estimatedCredits, onCostChange])

  const buildSummary = (type: ReportRequestKind, credits: number) => {
    return type === 'judicial'
      ? `${t('judicialReport')} • ${t('reportCreditsRequired')}: ${credits}`
      : `${t('historicalReport')} • ${t('reportCreditsRequired')}: ${credits}`
  }

  const submitJudicial = (values: ReportFormValues) => {
    const payload: JudicialReportRequest = {
      fire_event_id: values.fire_event_id,
      include_climate: values.include_climate,
      include_imagery: values.include_imagery,
      requester_name: values.requester_name || undefined,
      case_reference: values.case_reference || undefined,
      language: 'es',
    }

    reportMutation.mutate(
      {
        type: 'judicial',
        payload,
        idempotencyKey: globalThis.crypto?.randomUUID?.() ?? undefined,
      },
      {
        onSuccess: (response) => {
          onReportCreated({
            reportType: 'judicial',
            requiredCredits: estimatedCredits,
            response,
          })
        },
        onError: (error) => {
          onError?.(error.message)
        },
      },
    )
  }

  const submitHistorical = (values: ReportFormValues) => {
    const payload: HistoricalReportRequest = {
      protected_area_id: values.protected_area_id || undefined,
      protected_area_name: values.protected_area_name || undefined,
      start_date: values.start_date,
      end_date: values.end_date,
      include_monthly_images: values.include_monthly_images,
      max_images: Number(values.max_images),
      language: 'es',
    }

    reportMutation.mutate(
      {
        type: 'historical',
        payload,
        idempotencyKey: globalThis.crypto?.randomUUID?.() ?? undefined,
      },
      {
        onSuccess: (response) => {
          onReportCreated({
            reportType: 'historical',
            requiredCredits: estimatedCredits,
            response,
          })
        },
        onError: (error) => {
          onError?.(error.message)
        },
      },
    )
  }

  const handleSubmit = (values: ReportFormValues) => {
    onResetStatus?.()
    onError?.(null)

    if (creditsBalance === null || creditsBalance < estimatedCredits) {
      onPendingApproval({
        reportType: values.report_type,
        requiredCredits: estimatedCredits,
        requestedAt: new Date().toISOString(),
        summary: buildSummary(values.report_type, estimatedCredits),
      })
      return
    }

    if (values.report_type === 'judicial') {
      submitJudicial(values)
      return
    }

    submitHistorical(values)
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-primary" />
          {t('reportsTitle')}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
            <FormField
              control={form.control}
              name="report_type"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('reportType')}</FormLabel>
                  <FormControl>
                    <RadioGroup
                      value={field.value}
                      onValueChange={field.onChange}
                      className="grid gap-4 sm:grid-cols-2"
                    >
                      <label className="flex cursor-pointer items-center gap-3 rounded-lg border border-border p-4 transition-colors hover:bg-muted">
                        <RadioGroupItem value="judicial" />
                        <div>
                          <p className="font-semibold text-foreground">{t('judicialReport')}</p>
                          <p className="text-xs text-muted-foreground">{t('judicialReportHint')}</p>
                        </div>
                      </label>
                      <label className="flex cursor-pointer items-center gap-3 rounded-lg border border-border p-4 transition-colors hover:bg-muted">
                        <RadioGroupItem value="historical" />
                        <div>
                          <p className="font-semibold text-foreground">{t('historicalReport')}</p>
                          <p className="text-xs text-muted-foreground">{t('historicalReportHint')}</p>
                        </div>
                      </label>
                    </RadioGroup>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {reportType === 'judicial' ? (
              <div className="grid gap-4 sm:grid-cols-2">
                <FormField
                  control={form.control}
                  name="fire_event_id"
                  render={({ field }) => (
                    <FormItem className="sm:col-span-2">
                      <FormLabel>{t('reportFireEventId')}</FormLabel>
                      <FormControl>
                        <Input {...field} placeholder="550e8400-e29b-41d4-a716-446655440000" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="requester_name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t('reportRequesterName')}</FormLabel>
                      <FormControl>
                        <Input {...field} placeholder="Nombre completo" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="case_reference"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t('reportCaseReference')}</FormLabel>
                      <FormControl>
                        <Input {...field} placeholder="EXP-2026-001" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="include_imagery"
                  render={({ field }) => (
                    <FormItem className="flex items-center gap-3 rounded-lg border border-border p-4">
                      <FormControl>
                        <Checkbox checked={field.value} onCheckedChange={field.onChange} />
                      </FormControl>
                      <div>
                        <FormLabel>{t('reportIncludeImagery')}</FormLabel>
                        <p className="text-xs text-muted-foreground">{t('reportIncludeImageryHint')}</p>
                      </div>
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="include_climate"
                  render={({ field }) => (
                    <FormItem className="flex items-center gap-3 rounded-lg border border-border p-4">
                      <FormControl>
                        <Checkbox checked={field.value} onCheckedChange={field.onChange} />
                      </FormControl>
                      <div>
                        <FormLabel>{t('reportIncludeClimate')}</FormLabel>
                        <p className="text-xs text-muted-foreground">{t('reportIncludeClimateHint')}</p>
                      </div>
                    </FormItem>
                  )}
                />
              </div>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2">
                <FormField
                  control={form.control}
                  name="protected_area_id"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t('reportProtectedAreaId')}</FormLabel>
                      <FormControl>
                        <Input {...field} placeholder="UUID (opcional)" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="protected_area_name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t('reportProtectedAreaName')}</FormLabel>
                      <FormControl>
                        <Input {...field} placeholder="Ej: Parque Nacional Los Glaciares" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="start_date"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t('reportStartDate')}</FormLabel>
                      <FormControl>
                        <Input {...field} type="date" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="end_date"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t('reportEndDate')}</FormLabel>
                      <FormControl>
                        <Input {...field} type="date" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="max_images"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t('reportMaxImages')}</FormLabel>
                      <FormControl>
                        <Input {...field} type="number" min={1} max={12} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="include_monthly_images"
                  render={({ field }) => (
                    <FormItem className="flex items-center gap-3 rounded-lg border border-border p-4">
                      <FormControl>
                        <Checkbox checked={field.value} onCheckedChange={field.onChange} />
                      </FormControl>
                      <div>
                        <FormLabel>{t('reportIncludeMonthly')}</FormLabel>
                        <p className="text-xs text-muted-foreground">{t('reportIncludeMonthlyHint')}</p>
                      </div>
                    </FormItem>
                  )}
                />
              </div>
            )}

            <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-muted/40 px-4 py-3">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                {reportType === 'judicial' ? (
                  <Scale className="h-4 w-4" />
                ) : (
                  <CalendarRange className="h-4 w-4" />
                )}
                {t('reportEstimatedCost')}
              </div>
              <Badge variant="secondary">{estimatedCredits}</Badge>
            </div>

            <Button type="submit" disabled={!form.formState.isValid || reportMutation.isPending}>
              {reportMutation.isPending ? t('loading') : t('reportSubmit')}
            </Button>
          </form>
        </Form>
      </CardContent>
    </Card>
  )
}
