import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import RegisterPage from '../Register'
import { useAuth } from '@/context/AuthContext'

// Mocks
vi.mock('@/context/LanguageContext', () => ({
    useI18n: () => ({
        t: (key: string) => key,
    })
}))

vi.mock('@/context/AuthContext', () => ({
    useAuth: vi.fn(),
}))

const mockSignUpWithEmail = vi.fn()

describe('RegisterPage Validation', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        vi.mocked(useAuth).mockReturnValue({
            signIn: vi.fn(),
            signInWithGoogle: vi.fn(),
            signInWithOtp: vi.fn(),
            status: 'unauthenticated',
            isAuthenticated: false,
            user: null,
            session: null,
            role: 'anonymous',
            signOut: vi.fn(),
            signUpWithEmail: mockSignUpWithEmail,
        })
    })

    const renderWithRouter = () => {
        return render(
            <MemoryRouter>
                <RegisterPage />
            </MemoryRouter>
        )
    }

    it('renders all inputs correctly', () => {
        renderWithRouter()
        expect(screen.getByLabelText('firstName')).toBeInTheDocument()
        expect(screen.getByLabelText('lastName')).toBeInTheDocument()
        expect(screen.getByLabelText('email')).toBeInTheDocument()
        expect(screen.getByLabelText('password')).toBeInTheDocument()
        expect(screen.getByLabelText('Confirmar contraseña')).toBeInTheDocument()
    })

    it('shows validation error for empty submission', async () => {
        renderWithRouter()
        const user = userEvent.setup()
        await user.click(screen.getByRole('button', { name: /registerAction/i }))

        await waitFor(() => {
            expect(screen.getAllByText('validationRequired')).toHaveLength(2) // firstName, lastName
            expect(screen.getByText('validationInvalidEmail')).toBeInTheDocument()
            expect(screen.getByText('La contraseña es obligatoria para crear tu cuenta.')).toBeInTheDocument()
        })
    })

    it('shows password complexity errors', async () => {
        renderWithRouter()
        const user = userEvent.setup()

        // Type short password
        const passwordInput = screen.getByLabelText('password')
        await user.type(passwordInput, 'abc')
        await user.click(screen.getByRole('button', { name: /registerAction/i }))

        await waitFor(() => {
            expect(screen.getByText('La contraseña es demasiado corta. Necesita al menos 8 caracteres.')).toBeInTheDocument()
        })

        // Type password without number/symbol
        await user.clear(passwordInput)
        await user.type(passwordInput, 'Abcdefgh')
        await user.click(screen.getByRole('button', { name: /registerAction/i }))

        await waitFor(() => {
            expect(screen.getByText('La contraseña debe incluir al menos un número y un símbolo.')).toBeInTheDocument()
        })
    })

    it('shows password matching error', async () => {
        renderWithRouter()
        const user = userEvent.setup()

        await user.type(screen.getByLabelText('password'), 'Valid123!')
        await user.type(screen.getByLabelText('Confirmar contraseña'), 'Valid123') // Missing exclamation
        await user.click(screen.getByRole('button', { name: /registerAction/i }))

        await waitFor(() => {
            expect(screen.getByText('Las contraseñas ingresadas no coinciden. Verifícalas usando el icono del ojo.')).toBeInTheDocument()
        })
    })

    it('submits successfully with valid data', async () => {
        renderWithRouter()
        const user = userEvent.setup()

        await user.type(screen.getByLabelText('firstName'), 'John')
        await user.type(screen.getByLabelText('lastName'), 'Doe')
        await user.type(screen.getByLabelText('email'), 'john@example.com')
        await user.type(screen.getByLabelText('password'), 'Valid123!')
        await user.type(screen.getByLabelText('Confirmar contraseña'), 'Valid123!')

        await user.click(screen.getByRole('button', { name: /registerAction/i }))

        await waitFor(() => {
            expect(mockSignUpWithEmail).toHaveBeenCalledWith(
                expect.objectContaining({
                    email: 'john@example.com',
                    password: 'Valid123!'
                })
            )
        })
    })
})
