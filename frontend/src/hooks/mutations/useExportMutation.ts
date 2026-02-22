/**
 * @file useExportMutation.ts
 * @description Mutation para exportar incendios y descargar blob.
 */

import { useMutation } from '@tanstack/react-query'
import { exportFires } from '@/services/endpoints/fires'
import type { ExportRequestStatus, FireFilters } from '@/types/fire'

const DEFAULT_PREFIX = 'incendios_historicos'

const buildFilename = (prefix: string) => {
  const date = new Date().toISOString().split('T')[0]
  return `${prefix}_${date}.csv`
}

const downloadBlob = (blob: Blob, filename: string) => {
  if (typeof window === 'undefined' || typeof document === 'undefined') return
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

export function useExportMutation(filePrefix: string = DEFAULT_PREFIX) {
  return useMutation({
    mutationFn: async (filters?: FireFilters) => exportFires(filters),
    onSuccess: (result) => {
      if (result instanceof Blob) {
        downloadBlob(result, buildFilename(filePrefix))
      }
    },
  })
}

export type ExportMutationResult = ExportRequestStatus | Blob
