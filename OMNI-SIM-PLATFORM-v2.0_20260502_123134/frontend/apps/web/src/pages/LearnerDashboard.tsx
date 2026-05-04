import { Trophy, BookOpen, Clock, TrendingUp, User, Settings } from 'lucide-react'
import { AchievementGrid } from '../components/AchievementCard'
import type { Course, Achievement } from '../types'

interface LearnerDashboardProps {
  courses: Course[]
  achievements: Achievement[]
  progress: Record<number, { completed: number; total: number }>
}

export default function LearnerDashboard({ courses, achievements, progress }: LearnerDashboardProps) {
  const stats = [
    {
      label: '完成课程',
      value: Object.values(progress).filter(p => p.completed === p.total && p.total > 0).length,
      icon: BookOpen,
      color: 'blue'
    },
    {
      label: '学习中',
      value: courses.length - Object.values(progress).filter(p => p.completed === p.total && p.total > 0).length,
      icon: Clock,
      color: 'amber'
    },
    {
      label: '获得成就',
      value: achievements.length,
      icon: Trophy,
      color: 'green'
    },
    {
      label: '学习进度',
      value: '75%',
      icon: TrendingUp,
      color: 'purple'
    }
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center">
                <User className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-gray-800">学员学习中心</h1>
                <p className="text-xs text-gray-500">继续加油！</p>
              </div>
            </div>
            <button className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg">
              <Settings className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {stats.map((stat) => (
            <div key={stat.label} className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center mb-3 bg-${stat.color}-100 text-${stat.color}-600`}>
                <stat.icon className="w-5 h-5" />
              </div>
              <p className="text-2xl font-bold text-gray-800">{stat.value}</p>
              <p className="text-sm text-gray-500">{stat.label}</p>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
              <h2 className="text-lg font-semibold text-gray-800 mb-4">我的课程</h2>
              <div className="space-y-4">
                {courses.map((course) => (
                  <div
                    key={course.id}
                    className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                        <BookOpen className="w-6 h-6 text-blue-600" />
                      </div>
                      <div>
                        <h3 className="font-medium text-gray-800">{course.name}</h3>
                        <p className="text-sm text-gray-500">
                          {progress[course.id]?.completed || 0} / {progress[course.id]?.total || 0} 关卡
                        </p>
                      </div>
                    </div>
                    <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-blue-500 transition-all"
                        style={{
                          width: progress[course.id]?.total
                            ? `${(progress[course.id].completed / progress[course.id].total) * 100}%`
                            : '0%'
                        }}
                      />
                    </div>
                  </div>
                ))}
                {courses.length === 0 && (
                  <p className="text-center text-gray-500 py-8">暂无课程</p>
                )}
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
              <AchievementGrid achievements={achievements} totalUnlocked={achievements.length} />
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
