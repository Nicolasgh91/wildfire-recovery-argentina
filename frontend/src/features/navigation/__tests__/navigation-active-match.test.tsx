import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, NavLink } from 'react-router-dom'
import {
  PRIMARY_NAVIGATION_ITEMS,
  navLinkShouldUseExactMatch,
  type NavigationActiveMatch,
} from '@/features/navigation/config/navigation'

function NavLinkProbe(props: {
  to: string
  activeMatch: NavigationActiveMatch
  initialPath: string
}) {
  return (
    <MemoryRouter initialEntries={[props.initialPath]}>
      <NavLink
        to={props.to}
        end={navLinkShouldUseExactMatch(props.activeMatch)}
        className={({ isActive }) => (isActive ? 'active' : 'inactive')}
      >
        nav-item
      </NavLink>
    </MemoryRouter>
  )
}

describe('navigation activeMatch', () => {
  it('uses prefix matching for the fire history parent item', () => {
    const fireHistoryItem = PRIMARY_NAVIGATION_ITEMS.find((item) => item.to === '/fires/history')
    expect(fireHistoryItem?.activeMatch).toBe('prefix')
  })

  it('keeps parent item active with prefix matching on dynamic descendant routes', () => {
    render(<NavLinkProbe to="/fires/history" activeMatch="prefix" initialPath="/fires/history/abc123" />)
    expect(screen.getByRole('link', { name: 'nav-item' })).toHaveClass('active')
  })

  it('does not keep exact routes active outside their exact path', () => {
    render(<NavLinkProbe to="/map" activeMatch="exact" initialPath="/map/child" />)
    expect(screen.getByRole('link', { name: 'nav-item' })).toHaveClass('inactive')
  })
})

