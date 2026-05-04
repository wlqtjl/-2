import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Users, BookOpen, Trophy, BarChart3, Settings, Trash2,
  Edit, Plus, ChevronRight, Shield, Activity, AlertTriangle,
  CheckCircle, XCircle, Clock, GraduationCap, TrendingUp
} from 'lucide-react'
import { adminAPI } from '../api'

interface DashboardStats {
  total_users: number
  active_users: number
  total_courses: number
  published_courses: number
  total_levels: number
  total_questions: number
  total_attempts: number
  completion_rate: number
}

interface User {
  id: number
  email: string
  full_name: string | null
  role: string
  is_active: boolean
  created_at: string
}

interface Course {
  id: number
  name: string
  description: string | null
  status: string
  created_at: string
  level_count: number
}

interface SystemHealth {
  database: string
  redis: string
  cpu_percent: number
  memory_percent: number
  disk_percent: number
}

type TabType = 'dashboard' | 'users' | 'courses' | 'analytics'

export default function AdminDashboard() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<TabType>('dashboard')
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [users, setUsers] = useState<User[]>([])
  const [courses, setCourses] = useState<Course[]>([])
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null)
  const [userPage, setUserPage] = useState(1)
  const [coursePage, setCoursePage] = useState(1)
  const [userSearch, setUserSearch] = useState('')
  const [courseSearch, setCourseSearch] = useState('')
  const [userRoleFilter, setUserRoleFilter] = useState('')
  const [courseStatusFilter, setCourseStatusFilter] = useState('')

  useEffect(() => {
    checkAdminAccess()
    loadDashboardStats()
    loadSystemHealth()
  }, [])

  useEffect(() => {
    if (activeTab === 'users') loadUsers()
    if (activeTab === 'courses') loadCourses()
  }, [activeTab, userPage, userSearch, userRoleFilter, coursePage, courseSearch, courseStatusFilter])

  const checkAdminAccess = () => {
    const token = localStorage.getItem('token')
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]))
        if (payload.role !== 'admin') {
          alert('您没有管理员权限')
          navigate('/')
        }
      } catch (e) {
        navigate('/login')
      }
    } else {
      navigate('/login')
    }
  }

  const loadDashboardStats = async () => {
    try {
      const data = await adminAPI.getDashboardStats()
      setStats(data)
    } catch (err) {
      console.error('Failed to load stats:', err)
    } finally {
      setLoading(false)
    }
  }

  const loadSystemHealth = async () => {
    try {
      const data = await adminAPI.getSystemHealth()
      setSystemHealth(data)
    } catch (err) {
      console.error('Failed to load system health:', err)
    }
  }

  const loadUsers = async () => {
    try {
      const data = await adminAPI.getUsers({
        page: userPage,
        page_size: 10,
        role: userRoleFilter || undefined,
        search: userSearch || undefined
      })
      setUsers(data.users)
    } catch (err) {
      console.error('Failed to load users:', err)
    }
  }

  const loadCourses = async () => {
    try {
      const data = await adminAPI.getCourses({
        page: coursePage,
        page_size: 10,
        status: courseStatusFilter || undefined,
        search: courseSearch || undefined
      })
      setCourses(data.courses)
    } catch (err) {
      console.error('Failed to load courses:', err)
    }
  }

  const handleUpdateUser = async (userId: number, role?: string, isActive?: boolean) => {
    try {
      await adminAPI.updateUser(userId, { role, is_active: isActive })
      loadUsers()
      alert('用户更新成功')
    } catch (err) {
      alert('更新失败')
    }
  }

  const handleDeleteUser = async (userId: number) => {
    if (!confirm('确定要删除该用户吗？')) return
    try {
      await adminAPI.deleteUser(userId)
      loadUsers()
      alert('用户删除成功')
    } catch (err) {
      alert('删除失败')
    }
  }

  const handleDeleteCourse = async (courseId: number) => {
    if (!confirm('确定要删除该课程吗？')) return
    try {
      await adminAPI.deleteCourse(courseId)
      loadCourses()
      loadDashboardStats()
      alert('课程删除成功')
    } catch (err) {
      alert('删除失败')
    }
  }

  const handleUpdateCourse = async (courseId: number, status?: string) => {
    try {
      await adminAPI.updateCourse(courseId, { status })
      loadCourses()
      loadDashboardStats()
      alert('课程更新成功')
    } catch (err) {
      alert('更新失败')
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-red-600 to-pink-600 rounded-xl flex items-center justify-center">
                <Shield className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-800">管理后台</h1>
                <p className="text-xs text-gray-500">游戏化培训平台 v2.0</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <button
                onClick={() => navigate('/')}
                className="flex items-center gap-2 px-4 py-2 bg-blue-50 text-blue-600 hover:bg-blue-100 rounded-lg transition-colors"
              >
                返回首页
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex gap-6">
          <aside className="w-64 flex-shrink-0">
            <nav className="bg-white rounded-xl shadow-sm p-4 space-y-1">
              <button
                onClick={() => setActiveTab('dashboard')}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                  activeTab === 'dashboard'
                    ? 'bg-blue-50 text-blue-600'
                    : 'text-gray-600 hover:bg-gray-50'
                }`}
              >
                <BarChart3 className="w-5 h-5" />
                <span className="font-medium">数据概览</span>
              </button>
              <button
                onClick={() => setActiveTab('users')}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                  activeTab === 'users'
                    ? 'bg-blue-50 text-blue-600'
                    : 'text-gray-600 hover:bg-gray-50'
                }`}
              >
                <Users className="w-5 h-5" />
                <span className="font-medium">用户管理</span>
              </button>
              <button
                onClick={() => setActiveTab('courses')}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                  activeTab === 'courses'
                    ? 'bg-blue-50 text-blue-600'
                    : 'text-gray-600 hover:bg-gray-50'
                }`}
              >
                <BookOpen className="w-5 h-5" />
                <span className="font-medium">课程管理</span>
              </button>
              <button
                onClick={() => setActiveTab('analytics')}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                  activeTab === 'analytics'
                    ? 'bg-blue-50 text-blue-600'
                    : 'text-gray-600 hover:bg-gray-50'
                }`}
              >
                <TrendingUp className="w-5 h-5" />
                <span className="font-medium">数据分析</span>
              </button>
            </nav>
          </aside>

          <main className="flex-1">
            {activeTab === 'dashboard' && stats && (
              <div className="space-y-6">
                <h2 className="text-2xl font-bold text-gray-800">数据概览</h2>

                <div className="grid grid-cols-4 gap-6">
                  <div className="bg-white rounded-xl shadow-sm p-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-500">总用户数</p>
                        <p className="text-3xl font-bold text-gray-800 mt-1">{stats.total_users}</p>
                      </div>
                      <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center">
                        <Users className="w-6 h-6 text-blue-600" />
                      </div>
                    </div>
                    <p className="text-sm text-green-600 mt-2">活跃用户: {stats.active_users}</p>
                  </div>

                  <div className="bg-white rounded-xl shadow-sm p-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-500">课程总数</p>
                        <p className="text-3xl font-bold text-gray-800 mt-1">{stats.total_courses}</p>
                      </div>
                      <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center">
                        <BookOpen className="w-6 h-6 text-purple-600" />
                      </div>
                    </div>
                    <p className="text-sm text-green-600 mt-2">已发布: {stats.published_courses}</p>
                  </div>

                  <div className="bg-white rounded-xl shadow-sm p-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-500">关卡总数</p>
                        <p className="text-3xl font-bold text-gray-800 mt-1">{stats.total_levels}</p>
                      </div>
                      <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center">
                        <Trophy className="w-6 h-6 text-green-600" />
                      </div>
                    </div>
                    <p className="text-sm text-gray-500 mt-2">题目数: {stats.total_questions}</p>
                  </div>

                  <div className="bg-white rounded-xl shadow-sm p-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-500">完成率</p>
                        <p className="text-3xl font-bold text-gray-800 mt-1">{(stats.completion_rate * 100).toFixed(1)}%</p>
                      </div>
                      <div className="w-12 h-12 bg-amber-100 rounded-xl flex items-center justify-center">
                        <Activity className="w-6 h-6 text-amber-600" />
                      </div>
                    </div>
                    <p className="text-sm text-gray-500 mt-2">总尝试: {stats.total_attempts}</p>
                  </div>
                </div>

                {systemHealth && (
                  <div className="bg-white rounded-xl shadow-sm p-6">
                    <h3 className="text-lg font-semibold text-gray-800 mb-4">系统健康状态</h3>
                    <div className="grid grid-cols-4 gap-4">
                      <div className="flex items-center gap-3">
                        {systemHealth.database === 'healthy' ? (
                          <CheckCircle className="w-5 h-5 text-green-500" />
                        ) : (
                          <XCircle className="w-5 h-5 text-red-500" />
                        )}
                        <span className="text-sm text-gray-600">数据库</span>
                      </div>
                      <div className="flex items-center gap-3">
                        {systemHealth.redis === 'healthy' ? (
                          <CheckCircle className="w-5 h-5 text-green-500" />
                        ) : (
                          <XCircle className="w-5 h-5 text-red-500" />
                        )}
                        <span className="text-sm text-gray-600">Redis</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-sm text-gray-600">CPU: {systemHealth.cpu_percent.toFixed(1)}%</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-sm text-gray-600">内存: {systemHealth.memory_percent.toFixed(1)}%</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'users' && (
              <div className="space-y-6">
                <div className="bg-white rounded-xl shadow-sm p-6">
                  <h3 className="text-lg font-semibold text-gray-800 mb-4">用户管理</h3>

                  <div className="flex gap-4 mb-6">
                    <input
                      type="text"
                      placeholder="搜索用户名或邮箱..."
                      value={userSearch}
                      onChange={(e) => setUserSearch(e.target.value)}
                      className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                    <select
                      value={userRoleFilter}
                      onChange={(e) => setUserRoleFilter(e.target.value)}
                      className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    >
                      <option value="">全部角色</option>
                      <option value="admin">管理员</option>
                      <option value="instructor">讲师</option>
                      <option value="learner">学员</option>
                    </select>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-gray-200">
                          <th className="text-left py-3 px-4 text-sm font-semibold text-gray-600">用户</th>
                          <th className="text-left py-3 px-4 text-sm font-semibold text-gray-600">角色</th>
                          <th className="text-left py-3 px-4 text-sm font-semibold text-gray-600">状态</th>
                          <th className="text-left py-3 px-4 text-sm font-semibold text-gray-600">注册时间</th>
                          <th className="text-right py-3 px-4 text-sm font-semibold text-gray-600">操作</th>
                        </tr>
                      </thead>
                      <tbody>
                        {users.map((user) => (
                          <tr key={user.id} className="border-b border-gray-100 hover:bg-gray-50">
                            <td className="py-3 px-4">
                              <div>
                                <p className="font-medium text-gray-800">{user.full_name || '未设置'}</p>
                                <p className="text-sm text-gray-500">{user.email}</p>
                              </div>
                            </td>
                            <td className="py-3 px-4">
                              <select
                                value={user.role}
                                onChange={(e) => handleUpdateUser(user.id, e.target.value)}
                                className="px-2 py-1 border border-gray-300 rounded text-sm"
                              >
                                <option value="learner">学员</option>
                                <option value="instructor">讲师</option>
                                <option value="admin">管理员</option>
                              </select>
                            </td>
                            <td className="py-3 px-4">
                              <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs ${
                                user.is_active
                                  ? 'bg-green-100 text-green-700'
                                  : 'bg-red-100 text-red-700'
                              }`}>
                                {user.is_active ? <CheckCircle className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                                {user.is_active ? '活跃' : '禁用'}
                              </span>
                            </td>
                            <td className="py-3 px-4 text-sm text-gray-500">
                              {new Date(user.created_at).toLocaleDateString()}
                            </td>
                            <td className="py-3 px-4 text-right">
                              <button
                                onClick={() => handleUpdateUser(user.id, undefined, !user.is_active)}
                                className={`px-3 py-1 text-sm rounded ${
                                  user.is_active
                                    ? 'bg-red-100 text-red-600 hover:bg-red-200'
                                    : 'bg-green-100 text-green-600 hover:bg-green-200'
                                }`}
                              >
                                {user.is_active ? '禁用' : '启用'}
                              </button>
                              <button
                                onClick={() => handleDeleteUser(user.id)}
                                className="ml-2 px-3 py-1 text-sm bg-gray-100 text-gray-600 hover:bg-gray-200 rounded"
                              >
                                删除
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <div className="flex justify-center gap-2 mt-4">
                    <button
                      onClick={() => setUserPage(p => Math.max(1, p - 1))}
                      disabled={userPage === 1}
                      className="px-3 py-1 border rounded disabled:opacity-50"
                    >
                      上一页
                    </button>
                    <span className="px-3 py-1">第 {userPage} 页</span>
                    <button
                      onClick={() => setUserPage(p => p + 1)}
                      className="px-3 py-1 border rounded"
                    >
                      下一页
                    </button>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'courses' && (
              <div className="space-y-6">
                <div className="bg-white rounded-xl shadow-sm p-6">
                  <h3 className="text-lg font-semibold text-gray-800 mb-4">课程管理</h3>

                  <div className="flex gap-4 mb-6">
                    <input
                      type="text"
                      placeholder="搜索课程名称..."
                      value={courseSearch}
                      onChange={(e) => setCourseSearch(e.target.value)}
                      className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                    <select
                      value={courseStatusFilter}
                      onChange={(e) => setCourseStatusFilter(e.target.value)}
                      className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    >
                      <option value="">全部状态</option>
                      <option value="draft">草稿</option>
                      <option value="published">已发布</option>
                      <option value="archived">已归档</option>
                    </select>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-gray-200">
                          <th className="text-left py-3 px-4 text-sm font-semibold text-gray-600">课程</th>
                          <th className="text-left py-3 px-4 text-sm font-semibold text-gray-600">状态</th>
                          <th className="text-left py-3 px-4 text-sm font-semibold text-gray-600">关卡数</th>
                          <th className="text-left py-3 px-4 text-sm font-semibold text-gray-600">创建时间</th>
                          <th className="text-right py-3 px-4 text-sm font-semibold text-gray-600">操作</th>
                        </tr>
                      </thead>
                      <tbody>
                        {courses.map((course) => (
                          <tr key={course.id} className="border-b border-gray-100 hover:bg-gray-50">
                            <td className="py-3 px-4">
                              <div>
                                <p className="font-medium text-gray-800">{course.name}</p>
                                <p className="text-sm text-gray-500">{course.description || '无描述'}</p>
                              </div>
                            </td>
                            <td className="py-3 px-4">
                              <select
                                value={course.status}
                                onChange={(e) => handleUpdateCourse(course.id, e.target.value)}
                                className="px-2 py-1 border border-gray-300 rounded text-sm"
                              >
                                <option value="draft">草稿</option>
                                <option value="published">已发布</option>
                                <option value="archived">已归档</option>
                              </select>
                            </td>
                            <td className="py-3 px-4 text-sm text-gray-500">
                              {course.level_count}
                            </td>
                            <td className="py-3 px-4 text-sm text-gray-500">
                              {new Date(course.created_at).toLocaleDateString()}
                            </td>
                            <td className="py-3 px-4 text-right">
                              <button
                                onClick={() => navigate(`/course/${course.id}`)}
                                className="px-3 py-1 text-sm bg-blue-100 text-blue-600 hover:bg-blue-200 rounded mr-2"
                              >
                                查看
                              </button>
                              <button
                                onClick={() => handleDeleteCourse(course.id)}
                                className="px-3 py-1 text-sm bg-red-100 text-red-600 hover:bg-red-200 rounded"
                              >
                                删除
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <div className="flex justify-center gap-2 mt-4">
                    <button
                      onClick={() => setCoursePage(p => Math.max(1, p - 1))}
                      disabled={coursePage === 1}
                      className="px-3 py-1 border rounded disabled:opacity-50"
                    >
                      上一页
                    </button>
                    <span className="px-3 py-1">第 {coursePage} 页</span>
                    <button
                      onClick={() => setCoursePage(p => p + 1)}
                      className="px-3 py-1 border rounded"
                    >
                      下一页
                    </button>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'analytics' && (
              <div className="space-y-6">
                <div className="bg-white rounded-xl shadow-sm p-6">
                  <h3 className="text-lg font-semibold text-gray-800 mb-4">数据分析</h3>
                  <div className="grid grid-cols-2 gap-6">
                    <div className="p-4 bg-gray-50 rounded-lg">
                      <p className="text-sm text-gray-500">用户总数</p>
                      <p className="text-2xl font-bold text-gray-800">{stats?.total_users || 0}</p>
                    </div>
                    <div className="p-4 bg-gray-50 rounded-lg">
                      <p className="text-sm text-gray-500">活跃用户</p>
                      <p className="text-2xl font-bold text-green-600">{stats?.active_users || 0}</p>
                    </div>
                    <div className="p-4 bg-gray-50 rounded-lg">
                      <p className="text-sm text-gray-500">课程总数</p>
                      <p className="text-2xl font-bold text-gray-800">{stats?.total_courses || 0}</p>
                    </div>
                    <div className="p-4 bg-gray-50 rounded-lg">
                      <p className="text-sm text-gray-500">关卡完成率</p>
                      <p className="text-2xl font-bold text-blue-600">
                        {((stats?.completion_rate || 0) * 100).toFixed(1)}%
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </main>
        </div>
      </div>
    </div>
  )
}
