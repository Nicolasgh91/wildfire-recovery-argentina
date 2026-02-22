/**
 * @file contact.ts
 * @description Contact endpoints.
 */

import { apiClient } from '../api'
import type { ContactFormPayload, ContactResponse } from '@/types/contact'

export async function sendContactForm(payload: ContactFormPayload): Promise<ContactResponse> {
  const formData = new FormData()
  const fullName = payload.surname ? `${payload.name} ${payload.surname}`.trim() : payload.name
  const message = payload.message ?? payload.description ?? ''

  formData.append('name', fullName)
  formData.append('email', payload.email)
  formData.append('subject', payload.subject)
  formData.append('message', message)

  if (payload.attachment) {
    formData.append('attachment', payload.attachment)
  }

  const response = await apiClient.post<ContactResponse>('/contact', formData)
  return response.data
}