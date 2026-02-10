import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { FireHistorySkeleton } from '@/components/fires/FireHistorySkeleton'

describe('FireHistorySkeleton', () => {
  it('renders skeleton placeholders', () => {
    const { container } = render(<FireHistorySkeleton />)
    expect(container.querySelectorAll('.animate-pulse').length).toBeGreaterThan(0)
  })
})