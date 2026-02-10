export type ContactAttachmentMeta = {
  filename: string
  content_type: string
  size_bytes: number
  sha256: string
}

export type ContactResponse = {
  status: string
  request_id: string
  message: string
  attachment?: ContactAttachmentMeta | null
}

export type ContactFormPayload = {
  name: string
  surname?: string
  email: string
  subject: string
  message?: string
  description?: string
  attachment?: File | null
}