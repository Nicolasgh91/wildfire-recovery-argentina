import { cn } from '@/lib/utils'

describe('cn', () => {
  it('merges class names and resolves conflicts', () => {
    expect(cn('px-2', 'px-4')).toBe('px-4')
    expect(cn('text-sm', false && 'hidden', 'text-sm')).toBe('text-sm')
  })
})
