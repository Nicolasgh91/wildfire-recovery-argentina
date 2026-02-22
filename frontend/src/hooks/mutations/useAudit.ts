/**
 * @file useAudit.ts
 * @description Mutation para auditoría legal de uso del suelo.
 */

import { useMutation } from '@tanstack/react-query'
import { performAudit } from '@/services/endpoints/audit'
import type { AuditRequest, AuditResponse } from '@/types/audit'

export function useAuditMutation() {
  return useMutation<AuditResponse, Error, AuditRequest>({
    mutationFn: performAudit,
  })
}
