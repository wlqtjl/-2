import { useState, useEffect } from 'react'
import { TrendingUp, Users, Award, Clock, ChevronRight, Activity } from 'lucide-react'

interface SummaryCard {
  id: string
  title: string
  value: string | number
  change?: number
  change_type?: string
}

interface ChartData {
  date: string
  value: number
}

interface LevelPopularity {
  level_id: number
  name: string
  completions: number
  avg_score: number
}

export default function AnalyticsDashboard() {
  const [summaryCards, setSummaryCards] = useState<SummaryCard[]>([])
  const [userGrowth, setUserGrowth] = useState<ChartData[]>([])
  const [levelPopularity, setLevelPopularity] = useState<LevelPopularity[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchAnalyticsData()
  }, [])

  const fetchAnalyticsData = async () => {
    try {
      const mockCards: SummaryCard[] = [
        { id: '1', title: '总用户数', value: '1,247', change: 12.5, change_type: 'increase' },
        { id: '2', title: '活跃用户', value: '342', change: 8.2, change_type: 'increase' },
        { id: '3', title: '关卡完成率', value: '78.5%', change: 3.1, change_type: 'increase' },
        { id: '4', title: '平均分数', value: '85.6', change: 2.4, change_type: 'increase' }
      ]
      setSummaryCards(mockCards)

      const mockGrowth: ChartData[] = Array.from({ length: 30 }, (_, i) => ({
        date: `Day ${i + 1}`,
        value: 1000 + i * 15 + Math.floor(Math.random() * 50)
      }))
      setUserGrowth(mockGrowth)

      const mockLevels: LevelPopularity[] = [
        { level_id: 1, name: '入门训练', completions: 1245, avg_score: 92.3 },
        { level_id: 2, name: '进阶挑战', completions: 987, avg_score: 85.1 },
        { level_id: 3, name: '专家考核', completions: 654, avg_score: 78.9 },
        { level_id: 4, name: '实战演练', completions: 432, avg_score: 72.4 },
        { level_id: 5, name: '最终测试', completions: 321, avg_score: 68.2 }
      ]
      setLevelPopularity(mockLevels)
    } catch (err) {
      console.error('Failed to fetch analytics:', err)
    } finally {
      setLoading(false)
    }
  }

  const iconMap: Record<string, React.ReactNode> = {
    users: <Users className="w-6 h-6" />,
    award: <Award className="w-6 h-6" />,
    clock: <Clock className="w-6 h-6" />,
    activity: <Activity className="w-6 h-6" />
  }

  const colorMap = ['blue', 'green', 'purple', 'amber']

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full" />
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800">数据分析中心</h1>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {summaryCards.map((card, index) => (
          <div key={card.id} className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
            <div className="flex items-center justify-between mb-3">
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center bg-${colorMap[index]}-100 text-${colorMap[index]}-600`}>
                {iconMap[Object.keys(iconMap)[index]]}
              </div>
              {card.change && (
                <div className={`flex items-center gap-1 text-sm ${card.change_type === 'increase' ? 'text-green-600' : 'text-red-600'}`}>
                  <TrendingUp className="w-4 h-4" />
                  <span>{card.change}%</span>
                </div>
              )}
            </div>
            <p className="text-2xl font-bold text-gray-800">{card.value}</p>
            <p className="text-sm text-gray-500">{card.title}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">用户增长趋势</h2>
          <div className="h-64 flex items-end gap-1">
            {userGrowth.slice(-14).map((data, index) => (
              <div key={index} className="flex-1 flex flex-col items-center">
                <div
                  className="w-full bg-gradient-to-t from-blue-500 to-blue-300 rounded-t"
                  style={{ height: `${(data.value / 1500) * 100}%` }}
                />
                <span className="text-xs text-gray-400 mt-1">{data.date.split(' ')[1]}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">关卡热度排行</h2>
          <div className="space-y-3">
            {levelPopularity.map((level, index) => (
              <div key={level.level_id} className="flex items-center gap-4">
                <span className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                  index === 0 ? 'bg-amber-100 text-amber-700' :
                  index === 1 ? 'bg-gray-100 text-gray-700' :
                  index === 2 ? 'bg-orange-100 text-orange-700' :
                  'bg-blue-50 text-blue-600'
                }`}>
                  {index + 1}
                </span>
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium text-gray-800">{level.name}</span>
                    <span className="text-sm text-gray-500">{level.completions} 完成</span>
                  </div>
                  <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-500 rounded-full"
                      style={{ width: `${(level.completions / 1500) * 100}%` }}
                    />
                  </div>
                </div>
                <ChevronRight className="w-5 h-5 text-gray-400" />
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">学习路径进度</h2>
          <div className="space-y-4">
            {[
              { name: '基础入门', progress: 100 },
              { name: '技能进阶', progress: 78 },
              { name: '实战应用', progress: 45 },
              { name: '综合考核', progress: 12 }
            ].map((stage, index) => (
              <div key={index} className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-700">{stage.name}</span>
                  <span className="text-gray-500">{stage.progress}%</span>
                </div>
                <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      stage.progress === 100 ? 'bg-green-500' :
                      stage.progress > 50 ? 'bg-blue-500' :
                      'bg-amber-500'
                    }`}
                    style={{ width: `${stage.progress}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">错误分布</h2>
          <div className="space-y-3">
            {[
              { type: '超时错误', count: 234, percentage: 35.2 },
              { type: '答案错误', count: 189, percentage: 28.4 },
              { type: '网络异常', count: 145, percentage: 21.8 },
              { type: '其他错误', count: 97, percentage: 14.6 }
            ].map((error, index) => (
              <div key={index} className="space-y-1">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-700">{error.type}</span>
                  <span className="text-gray-500">{error.count} ({error.percentage}%)</span>
                </div>
                <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      index === 0 ? 'bg-red-500' :
                      index === 1 ? 'bg-amber-500' :
                      index === 2 ? 'bg-blue-500' :
                      'bg-gray-400'
                    }`}
                    style={{ width: `${error.percentage}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">性能趋势</h2>
          <div className="h-48 flex items-center justify-center">
            <div className="w-full space-y-2">
              {[
                { label: '响应时间', value: '145ms', status: 'good' },
                { label: '成功率', value: '99.2%', status: 'good' },
                { label: '并发用户', value: '342', status: 'good' },
                { label: '系统负载', value: '42%', status: 'good' }
              ].map((metric, index) => (
                <div key={index} className="flex items-center justify-between p-2 bg-gray-50 rounded-lg">
                  <span className="text-sm text-gray-600">{metric.label}</span>
                  <span className={`text-sm font-medium ${
                    metric.status === 'good' ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {metric.value}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
