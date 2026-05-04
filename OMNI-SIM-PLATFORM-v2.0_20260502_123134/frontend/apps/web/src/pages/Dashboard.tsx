import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Gamepad2, BookOpen, Trophy, LogOut, Play, Plus, ChevronRight, Users, Clock, LayoutDashboard, School, Award, Shield, Crosshair } from 'lucide-react'
import { courseAPI } from '../api'
import type { Course, Level } from '../types'

export default function Dashboard() {
  const navigate = useNavigate()
  const [courses, setCourses] = useState<Course[]>([])
  const [loading, setLoading] = useState(true)
  const [isInstructor, setIsInstructor] = useState(false)
  const [isAdmin, setIsAdmin] = useState(false)

  useEffect(() => {
    fetchCourses()
    checkUserRole()
  }, [])

  const checkUserRole = () => {
    const token = localStorage.getItem('token')
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]))
        setIsInstructor(['admin', 'instructor'].includes(payload.role))
        setIsAdmin(payload.role === 'admin')
      } catch (e) {
        setIsInstructor(false)
        setIsAdmin(false)
      }
    }
  }

  const fetchCourses = async () => {
    try {
      const data = await courseAPI.getCourses()
      setCourses(Array.isArray(data) ? data : [])
    } catch (err) {
      console.error('Failed to fetch courses:', err)
      setCourses([])
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    navigate('/login')
  }

  const handleCourseClick = (courseId: number) => {
    navigate(`/course/${courseId}`)
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-purple-600 rounded-xl flex items-center justify-center">
                <Gamepad2 className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-800">游戏化培训平台</h1>
                <p className="text-xs text-gray-500">学习，从未如此有趣</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <button
                onClick={() => {
                  const base = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000'
                  const token = localStorage.getItem('token') || ''
                  window.open(`${base}/game/index.html?token=${encodeURIComponent(token)}`, '_blank')
                }}
                className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-emerald-500 to-teal-600 text-white hover:from-emerald-600 hover:to-teal-700 rounded-lg transition-colors shadow-sm"
                title="启动 V2V 迁移 FPS 战役"
              >
                <Crosshair className="w-4 h-4" />
                FPS 战役
              </button>
              <button
                onClick={() => navigate('/leaderboard')}
                className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-yellow-500 to-orange-500 text-white hover:from-yellow-600 hover:to-orange-600 rounded-lg transition-colors shadow-sm"
              >
                <Award className="w-4 h-4" />
                排行榜
              </button>
              {isInstructor && (
                <button
                  onClick={() => navigate('/instructor')}
                  className="flex items-center gap-2 px-4 py-2 bg-purple-50 text-purple-600 hover:bg-purple-100 rounded-lg transition-colors"
                >
                  <LayoutDashboard className="w-4 h-4" />
                  讲师工作台
                </button>
              )}
              {isAdmin && (
                <button
                  onClick={() => navigate('/admin')}
                  className="flex items-center gap-2 px-4 py-2 bg-red-50 text-red-600 hover:bg-red-100 rounded-lg transition-colors"
                >
                  <Shield className="w-4 h-4" />
                  管理后台
                </button>
              )}
              <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-50 text-amber-700 rounded-full">
                <Trophy className="w-4 h-4" />
                <span className="font-medium text-sm">0 积分</span>
              </div>
              <button
                onClick={handleLogout}
                className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <LogOut className="w-4 h-4" />
                退出登录
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-gray-800 mb-2">欢迎回来！</h2>
          <p className="text-gray-500">选择一个课程开始你的学习之旅</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {courses.map((course) => (
            <div
              key={course.id}
              className="bg-white rounded-2xl shadow-sm overflow-hidden hover:shadow-lg transition-all cursor-pointer group"
              onClick={() => handleCourseClick(course.id)}
            >
              <div className="h-32 bg-gradient-to-br from-blue-500 to-purple-600 relative">
                <div className="absolute inset-0 bg-black/10" />
                <div className="absolute bottom-4 left-4">
                  <span className="px-2 py-1 bg-white/20 backdrop-blur-sm rounded-full text-white text-xs">
                    {course.status === 'published' ? '进行中' : '未发布'}
                  </span>
                </div>
              </div>

              <div className="p-5">
                <h3 className="font-bold text-lg text-gray-800 mb-2 group-hover:text-blue-600 transition-colors">
                  {course.name}
                </h3>
                <p className="text-sm text-gray-500 mb-4 line-clamp-2">
                  {course.description || '点击查看课程详情'}
                </p>

                <div className="flex items-center justify-between text-sm text-gray-400 mb-4">
                  <div className="flex items-center gap-1">
                    <BookOpen className="w-4 h-4" />
                    <span>{(course as any).levels?.length || 0} 关卡</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Clock className="w-4 h-4" />
                    <span>2-3小时</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Users className="w-4 h-4" />
                    <span>12人学习</span>
                  </div>
                </div>

                <button
                  className="w-full flex items-center justify-center gap-2 py-2.5 bg-blue-50 text-blue-600 rounded-xl font-medium hover:bg-blue-100 transition-colors"
                  onClick={(e) => {
                    e.stopPropagation()
                    handleCourseClick(course.id)
                  }}
                >
                  <Play className="w-4 h-4" />
                  开始学习
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}

          {courses.length === 0 && (
            <div className="col-span-full text-center py-16">
              <div className="w-20 h-20 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <BookOpen className="w-10 h-10 text-gray-400" />
              </div>
              <h3 className="text-xl font-semibold text-gray-800 mb-2">暂无课程</h3>
              <p className="text-gray-500 mb-6">请联系管理员添加课程</p>
            </div>
          )}
        </div>

        <div className="mt-12 bg-white rounded-2xl shadow-sm p-6">
          <h3 className="text-lg font-bold text-gray-800 mb-4">学习成就</h3>
          <div className="grid grid-cols-4 gap-4">
            {[
              { icon: '🎯', name: '初学者', desc: '完成第一个关卡' },
              { icon: '🔥', name: '连续挑战', desc: '连续完成3个关卡' },
              { icon: '🏆', name: '知识达人', desc: '获得满分' },
              { icon: '⭐', name: '学习之星', desc: '完成全部课程' },
            ].map((achievement, idx) => (
              <div key={idx} className="text-center p-4 bg-gray-50 rounded-xl">
                <div className="text-4xl mb-2">{achievement.icon}</div>
                <h4 className="font-medium text-gray-800">{achievement.name}</h4>
                <p className="text-xs text-gray-500 mt-1">{achievement.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  )
}
