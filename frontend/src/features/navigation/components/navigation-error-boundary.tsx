import { Component, type ErrorInfo, type ReactNode } from 'react'
import { NavigationErrorFallback } from '@/features/navigation/components/navigation-error-fallback'

interface NavigationErrorBoundaryProps {
  children: ReactNode
}

interface NavigationErrorBoundaryState {
  hasError: boolean
}

export class NavigationErrorBoundary extends Component<
  NavigationErrorBoundaryProps,
  NavigationErrorBoundaryState
> {
  state: NavigationErrorBoundaryState = { hasError: false }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(_error: Error, _info: ErrorInfo) {
    // Errors surface via render
  }

  render() {
    if (this.state.hasError) {
      return <NavigationErrorFallback />
    }
    return this.props.children
  }
}

