import { useEffect, useMemo, useRef, useState } from 'react'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { Loader2, Paperclip, Send, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useToast } from '@/hooks/use-toast'
import { useAuth } from '@/context/AuthContext'
import { useI18n } from '@/context/LanguageContext'
import { sendContactForm } from '@/services/endpoints/contact'

const MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024
const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'application/pdf']

type ContactFormValues = {
  name: string
  surname?: string
  email: string
  subject: string
  description: string
  attachment?: File
}

const buildInitialValues = (): ContactFormValues => ({
  name: '',
  surname: '',
  email: '',
  subject: '',
  description: '',
  attachment: undefined,
})

export function ContactForm() {
  const { user, isAuthenticated } = useAuth()
  const { toast } = useToast()
  const { t } = useI18n()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const subjectOptions = [
    { value: 'support', label: t('contactSubjectSupport') },
    { value: 'sales', label: t('contactSubjectSales') },
    { value: 'other', label: t('contactSubjectOther') },
  ]

  const contactSchema = z.object({
    name: z.string().min(2, t('contactValidationNameRequired')).max(100, t('contactValidationNameTooLong')),
    surname: z.string().max(100, t('contactValidationSurnameTooLong')).optional().or(z.literal('')),
    email: z.string().email(t('contactValidationEmailInvalid')),
    subject: z.string().min(3, t('contactValidationSubjectRequired')).max(150, t('contactValidationSubjectTooLong')),
    description: z.string().min(10, t('contactValidationDescriptionShort')).max(5000, t('contactValidationDescriptionTooLong')),
    attachment: z
      .instanceof(File)
      .optional()
      .refine((file) => !file || file.size <= MAX_ATTACHMENT_BYTES, {
        message: t('contactValidationAttachmentTooLarge'),
      })
      .refine((file) => !file || ALLOWED_TYPES.includes(file.type), {
        message: t('contactValidationAttachmentType'),
      }),
  })

  const form = useForm<ContactFormValues>({
    resolver: zodResolver(contactSchema),
    defaultValues: buildInitialValues(),
    mode: 'onChange',
  })

  const attachment = form.watch('attachment')

  const fullName = useMemo(() => {
    const metadata = (user?.user_metadata || {}) as Record<string, string>
    return typeof metadata.full_name === 'string' ? metadata.full_name : ''
  }, [user])

  const lockNameFields = isAuthenticated && !!fullName

  useEffect(() => {
    if (user?.email) {
      form.setValue('email', user.email, { shouldValidate: true })
    }

    if (fullName) {
      const [first, ...rest] = fullName.split(' ')
      if (first) form.setValue('name', first, { shouldValidate: true })
      if (rest.length) {
        form.setValue('surname', rest.join(' '), { shouldValidate: true })
      }
    }
  }, [form, fullName, user?.email])

  useEffect(() => {
    if (!attachment || !attachment.type.startsWith('image/')) {
      setPreviewUrl(null)
      return
    }

    const url = URL.createObjectURL(attachment)
    setPreviewUrl(url)

    return () => {
      URL.revokeObjectURL(url)
    }
  }, [attachment])

  const handleFileChange = (file: File | null) => {
    form.setValue('attachment', file ?? undefined, { shouldValidate: true })
  }

  const resetAttachment = () => {
    form.setValue('attachment', undefined, { shouldValidate: true })
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const onSubmit = async (values: ContactFormValues) => {
    setIsSubmitting(true)

    try {
      await sendContactForm({
        name: values.name,
        surname: values.surname || undefined,
        email: values.email,
        subject: values.subject,
        description: values.description,
        attachment: values.attachment ?? undefined,
      })

      toast({
        title: t('contactToastSuccessTitle'),
        description: t('contactToastSuccessDescription'),
      })

      form.reset({
        ...buildInitialValues(),
        email: user?.email || '',
        name: lockNameFields ? form.getValues('name') : '',
        surname: lockNameFields ? form.getValues('surname') : '',
      })
      resetAttachment()
    } catch {
      toast({
        title: t('contactToastErrorTitle'),
        description: t('contactToastErrorDescription'),
        variant: 'destructive',
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('contactFormTitle')}</CardTitle>
        <CardDescription>
          {t('contactFormDescription')}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="name">{t('contactName')} *</Label>
              <Input
                id="name"
                {...form.register('name')}
                placeholder={t('contactNamePlaceholder')}
                readOnly={lockNameFields}
                className={lockNameFields ? 'bg-muted' : ''}
              />
              {form.formState.errors.name && (
                <p className="text-xs text-destructive">{form.formState.errors.name.message}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="surname">{t('contactSurname')}</Label>
              <Input
                id="surname"
                {...form.register('surname')}
                placeholder={t('contactSurnamePlaceholder')}
                readOnly={lockNameFields}
                className={lockNameFields ? 'bg-muted' : ''}
              />
              {form.formState.errors.surname && (
                <p className="text-xs text-destructive">
                  {form.formState.errors.surname.message}
                </p>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="email">{t('contactEmail')} *</Label>
            <Input
              id="email"
              type="email"
              {...form.register('email')}
              placeholder={t('contactEmailPlaceholder')}
              readOnly={isAuthenticated}
              className={isAuthenticated ? 'bg-muted' : ''}
            />
            {form.formState.errors.email && (
              <p className="text-xs text-destructive">{form.formState.errors.email.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="subject">{t('contactSubject')} *</Label>
            <Select
              value={form.watch('subject')}
              onValueChange={(value) => form.setValue('subject', value, { shouldValidate: true })}
            >
              <SelectTrigger id="subject">
                <SelectValue placeholder={t('contactSubjectPlaceholder')} />
              </SelectTrigger>
              <SelectContent>
                {subjectOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {form.formState.errors.subject && (
              <p className="text-xs text-destructive">{form.formState.errors.subject.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">{t('contactMessage')} *</Label>
            <Textarea
              id="description"
              {...form.register('description')}
              placeholder={t('contactDescriptionPlaceholder')}
              rows={5}
              className="resize-none"
            />
            {form.formState.errors.description && (
              <p className="text-xs text-destructive">
                {form.formState.errors.description.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label>{t('contactAttachment')}</Label>
            <div className="flex flex-wrap items-center gap-3">
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                accept=".pdf,.jpg,.jpeg,.png"
                onChange={(event) => handleFileChange(event.target.files?.[0] ?? null)}
              />
              <Button
                type="button"
                variant="outline"
                onClick={() => fileInputRef.current?.click()}
                className="gap-2"
              >
                <Paperclip className="h-4 w-4" />
                {t('contactSelectFile')}
              </Button>
              {attachment && (
                <div className="flex items-center gap-2 rounded-md bg-muted px-3 py-2 text-sm">
                  <span className="max-w-[200px] truncate">{attachment.name}</span>
                  <button
                    type="button"
                    onClick={resetAttachment}
                    className="text-muted-foreground hover:text-destructive"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              )}
            </div>
            {previewUrl && (
              <div className="mt-3">
                <img
                  src={previewUrl}
                  alt={t('contactAttachmentAlt')}
                  className="h-32 rounded-md border border-border object-cover"
                  loading="lazy"
                  decoding="async"
                />
              </div>
            )}
            {form.formState.errors.attachment && (
              <p className="text-xs text-destructive">
                {form.formState.errors.attachment.message}
              </p>
            )}
            <p className="text-xs text-muted-foreground">
              {t('contactAllowedFormats')}
            </p>
          </div>

          <Button type="submit" className="w-full gap-2" disabled={isSubmitting}>
            {isSubmitting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                {t('contactSending')}
              </>
            ) : (
              <>
                <Send className="h-4 w-4" />
                {t('contactSend')}
              </>
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
