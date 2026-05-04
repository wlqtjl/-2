import { ReactNode, useEffect, useState } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { authAPI } from '../api'

interface ProtectedRouteProps {
  children: ReactNode
  /** 允许访问该路由的角色列表；为空表示仅校验登录 */
  roles?: string[]
}

type LoadState = 'pending' | 'authorized' | 'unauthenticated' | 'forbidden'

export default function ProtectedRoute({ children, roles }: ProtectedRouteProps) {
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null
  const location = useLocation()
  const [state, setState] = useState<LoadState>(token ? 'pending' : 'unauthenticated')

  useEffect(() => {
    if (!token) {
      setState('unauthenticated')
      return
    }
    if (!roles || roles.length === 0) {
      setState('authorized')
      return
    }
    let cancelled = false
    authAPI
      .me()
      .then((user) => {
        if (cancelled) return
        if (user && user.role && roles.includes(user.role)) {
          setState('authorized')
        } else {
          setState('forbidden')
        }
      })
      .catch(() => {
        if (cancelled) return
        setState('unauthenticated')
      })
    return () => {
      cancelled = true
    }
  }, [token, roles])

  if (state === 'pending') {
    return <div className="min-h-screen flex items-center justify-center text-slate-500">校验权限中…</div>
  }
  if (state === 'unauthenticated') {
    return <Navigate to="/login" state={{ from: location }} replace />
  }
  if (state === 'forbidden') {
    return <Navigate to="/" replace />
  }
  return <>{children}</>
}
