import { Component, ErrorInfo, ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // 仅在控制台保留诊断信息；生产环境可接入 Sentry/Datadog 等。
    // eslint-disable-next-line no-console
    console.error('UI ErrorBoundary caught:', error, info)
  }

  handleReset = (): void => {
    this.setState({ hasError: false, error: null })
    if (typeof window !== 'undefined') {
      window.location.assign('/')
    }
  }

  handleReload = (): void => {
    if (typeof window !== 'undefined') {
      window.location.reload()
    }
  }

  render(): ReactNode {
    if (!this.state.hasError) return this.props.children

    const message =
      this.state.error?.message ?? '页面发生未知错误'

    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 p-6 text-slate-700 bg-slate-50">
        <h1 className="text-3xl font-bold text-red-600">出错了</h1>
        <p className="max-w-md text-center text-sm text-slate-600 break-words">
          {message}
        </p>
        <div className="flex gap-3">
          <button
            type="button"
            onClick={this.handleReset}
            className="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700"
          >
            返回首页
          </button>
          <button
            type="button"
            onClick={this.handleReload}
            className="px-4 py-2 rounded border border-slate-300 text-slate-700 hover:bg-slate-100"
          >
            重新加载
          </button>
        </div>
      </div>
    )
  }
}
