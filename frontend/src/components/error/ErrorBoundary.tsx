import { Component, type ReactNode } from 'react'
import { Button } from '@/components/ui/button'

interface ErrorBoundaryProps {
  children: ReactNode
}

interface ErrorBoundaryState {
  hasError: boolean
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(_error: Error, _info: React.ErrorInfo) {
    // Errors surface via render; optional: console.error in dev
  }

  handleRetry = () => {
    this.setState({ hasError: false })
    if (typeof window !== 'undefined') {
      window.location.reload()
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-background px-6 py-10">
          <div className="w-full max-w-md rounded-xl border border-border bg-card p-6 text-center">
            <h1 className="text-xl font-semibold text-foreground">Something went wrong</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Please try again. If the problem persists, contact support.
            </p>
            <Button className="mt-6 w-full" onClick={this.handleRetry}>
              Retry
            </Button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
