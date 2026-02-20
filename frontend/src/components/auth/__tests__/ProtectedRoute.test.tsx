import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ProtectedRoute } from '../ProtectedRoute'
import { AuthStatus } from '@/context/AuthContext'
import React from 'react'

const mockNavigate = vi.fn()
const mockLocation = { pathname: '/protected' }

vi.mock('react-router-dom', () => ({
    useNavigate: () => mockNavigate,
    useLocation: () => mockLocation,
    Navigate: ({ to, replace }: any) => <div data-testid="navigate" data-to={to} data-replace={replace ? 'true' : 'false'} />
}))

let mockAuthStatus: AuthStatus = 'authenticated'
let mockAuthRole = 'user'

vi.mock('@/context/AuthContext', () => ({
    useAuth: () => ({
        status: mockAuthStatus,
        role: mockAuthRole
    })
}))

vi.mock('@/context/LanguageContext', () => ({
    useI18n: () => ({
        t: (key: string) => key
    })
}))

describe('ProtectedRoute', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        mockAuthStatus = 'authenticated'
        mockAuthRole = 'user'
    })

    it('renders children when authenticated', () => {
        render(<ProtectedRoute><div data-testid="child" /></ProtectedRoute>)
        expect(screen.getByTestId('child')).toBeInTheDocument()
    })

    it('renders loading spinner when status is loading', () => {
        mockAuthStatus = 'loading'
        const { container } = render(<ProtectedRoute><div data-testid="child" /></ProtectedRoute>)
        expect(container.querySelector('.animate-spin')).toBeInTheDocument()
    })

    it('renders modal when unauthenticated with correct buttons', () => {
        mockAuthStatus = 'unauthenticated'
        render(<ProtectedRoute><div data-testid="child" /></ProtectedRoute>)

        expect(screen.getByText('protectedPageTitle')).toBeInTheDocument()
        expect(screen.getByText('protectedPageMessage')).toBeInTheDocument()
        expect(screen.queryByTestId('child')).not.toBeInTheDocument()

        const goBackButton = screen.getByText('goBack')
        const loginButton = screen.getByText('login')

        expect(goBackButton).toBeInTheDocument()
        expect(loginButton).toBeInTheDocument()

        fireEvent.click(goBackButton)
        expect(mockNavigate).toHaveBeenCalledWith(-1)

        fireEvent.click(loginButton)
        expect(mockNavigate).toHaveBeenCalledWith('/login', { state: { from: mockLocation } })
    })

    it('redirects when requiredRole is missing', () => {
        mockAuthStatus = 'authenticated'
        mockAuthRole = 'user'
        render(<ProtectedRoute requiredRole="admin"><div data-testid="child" /></ProtectedRoute>)

        const nav = screen.getByTestId('navigate')
        expect(nav).toBeInTheDocument()
        expect(nav).toHaveAttribute('data-to', '/home')
    })
})
