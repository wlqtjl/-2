import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { User, Mail, Lock, Gamepad2, Shield, GraduationCap, UserCircle, AlertCircle } from 'lucide-react'
import { authAPI } from '../api'

type RoleType = 'learner' | 'instructor' | 'admin'

interface FieldError {
  field: string
  message: string
}

interface ApiError {
  code: string
  message: string
  errors?: FieldError[]
}

export default function Register() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [role, setRole] = useState<RoleType>('learner')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string>('')
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    setFieldErrors({})

    if (password !== confirmPassword) {
      setFieldErrors({ confirmPassword: '两次输入的密码不一致' })
      setLoading(false)
      return
    }

    try {
      await authAPI.register(email, password, fullName, role)
      navigate('/login')
    } catch (err: any) {
      const errorData = err.response?.data?.detail
      
      if (errorData && typeof errorData === 'object') {
        const apiError = errorData as ApiError
        
        if (apiError.errors && Array.isArray(apiError.errors)) {
          const errors: Record<string, string> = {}
          apiError.errors.forEach((errItem: FieldError) => {
            errors[errItem.field] = errItem.message
          })
          setFieldErrors(errors)
        }
        
        setError(apiError.message || '注册失败，请稍后重试')
      } else {
        setError(err.message || '注册失败，请稍后重试')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-purple-50">
      <div className="card p-8 w-full max-w-md">
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <Gamepad2 className="w-8 h-8 text-purple-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-800">游戏化培训平台</h1>
          <p className="text-gray-500 mt-2">创建新账号</p>
        </div>

        <form onSubmit={handleSubmit}>
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">
              {error}
            </div>
          )}

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">姓名</label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className={`input-field pl-10 ${fieldErrors.full_name ? 'border-red-300 focus:ring-red-500 focus:border-red-500' : ''}`}
                placeholder="请输入姓名"
              />
            </div>
            {fieldErrors.full_name && (
              <p className="mt-1 text-sm text-red-600 flex items-center gap-1">
                <AlertCircle className="w-4 h-4" />
                {fieldErrors.full_name}
              </p>
            )}
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">邮箱</label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={`input-field pl-10 ${fieldErrors.email ? 'border-red-300 focus:ring-red-500 focus:border-red-500' : ''}`}
                placeholder="请输入邮箱"
                required
              />
            </div>
            {fieldErrors.email && (
              <p className="mt-1 text-sm text-red-600 flex items-center gap-1">
                <AlertCircle className="w-4 h-4" />
                {fieldErrors.email}
              </p>
            )}
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">密码</label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className={`input-field pl-10 ${fieldErrors.password ? 'border-red-300 focus:ring-red-500 focus:border-red-500' : ''}`}
                placeholder="请输入密码"
                required
              />
            </div>
            {fieldErrors.password && (
              <p className="mt-1 text-sm text-red-600 flex items-center gap-1">
                <AlertCircle className="w-4 h-4" />
                {fieldErrors.password}
              </p>
            )}
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">确认密码</label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className={`input-field pl-10 ${fieldErrors.confirmPassword ? 'border-red-300 focus:ring-red-500 focus:border-red-500' : ''}`}
                placeholder="请再次输入密码"
                required
              />
            </div>
            {fieldErrors.confirmPassword && (
              <p className="mt-1 text-sm text-red-600 flex items-center gap-1">
                <AlertCircle className="w-4 h-4" />
                {fieldErrors.confirmPassword}
              </p>
            )}
          </div>

          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">选择角色</label>
            <div className="grid grid-cols-3 gap-3">
              <button
                type="button"
                onClick={() => setRole('learner')}
                className={`flex flex-col items-center p-3 rounded-xl border-2 transition-all ${
                  role === 'learner'
                    ? 'border-blue-500 bg-blue-50 text-blue-700'
                    : 'border-gray-200 hover:border-gray-300 text-gray-600'
                }`}
              >
                <GraduationCap className="w-6 h-6 mb-1" />
                <span className="text-xs font-medium">学员</span>
              </button>
              <button
                type="button"
                onClick={() => setRole('instructor')}
                className={`flex flex-col items-center p-3 rounded-xl border-2 transition-all ${
                  role === 'instructor'
                    ? 'border-purple-500 bg-purple-50 text-purple-700'
                    : 'border-gray-200 hover:border-gray-300 text-gray-600'
                }`}
              >
                <UserCircle className="w-6 h-6 mb-1" />
                <span className="text-xs font-medium">讲师</span>
              </button>
              <button
                type="button"
                onClick={() => setRole('admin')}
                className={`flex flex-col items-center p-3 rounded-xl border-2 transition-all ${
                  role === 'admin'
                    ? 'border-red-500 bg-red-50 text-red-700'
                    : 'border-gray-200 hover:border-gray-300 text-gray-600'
                }`}
              >
                <Shield className="w-6 h-6 mb-1" />
                <span className="text-xs font-medium">管理员</span>
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                注册中...
              </>
            ) : (
              '注册'
            )}
          </button>
        </form>

        <p className="mt-6 text-center text-gray-500 text-sm">
          已有账号？ <Link to="/login" className="text-blue-600 hover:underline">立即登录</Link>
        </p>
      </div>
    </div>
  )
}
