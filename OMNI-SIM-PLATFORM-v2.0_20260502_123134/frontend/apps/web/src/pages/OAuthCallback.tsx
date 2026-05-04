import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

export default function OAuthCallback() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const token = searchParams.get('access_token')
    const err = searchParams.get('error')

    if (err) {
      setError(decodeURIComponent(err))
      return
    }

    if (token) {
      localStorage.setItem('token', token)
      navigate('/', { replace: true })
    } else {
      setError('OAuth 回调中未收到 access_token')
    }
  }, [searchParams, navigate])

  if (error) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 text-slate-600">
        <p className="text-red-500 font-medium">登录失败：{error}</p>
        <a href="/login" className="text-blue-600 hover:underline">返回登录</a>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
    </div>
  )
}
