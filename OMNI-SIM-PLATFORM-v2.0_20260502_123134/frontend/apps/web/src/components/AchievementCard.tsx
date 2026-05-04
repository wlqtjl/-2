import { Trophy, Star, Target, Zap, Award, Lock } from 'lucide-react'
import type { Achievement } from '../types'

interface AchievementCardProps {
  achievement: Achievement
  unlocked: boolean
}

export function AchievementCard({ achievement, unlocked }: AchievementCardProps) {
  const iconMap: Record<string, React.ReactNode> = {
    '🎯': <Target className="w-6 h-6" />,
    '⭐': <Star className="w-6 h-6" />,
    '🏆': <Trophy className="w-6 h-6" />,
    '💯': <Award className="w-6 h-6" />,
    '⚡': <Zap className="w-6 h-6" />
  }

  return (
    <div
      className={`relative p-4 rounded-xl border-2 transition-all ${
        unlocked
          ? 'bg-gradient-to-br from-amber-50 to-yellow-50 border-amber-300'
          : 'bg-gray-50 border-gray-200 opacity-60'
      }`}
    >
      <div className="flex items-start gap-3">
        <div
          className={`w-12 h-12 rounded-full flex items-center justify-center ${
            unlocked ? 'bg-amber-100 text-amber-600' : 'bg-gray-200 text-gray-400'
          }`}
        >
          {unlocked ? (
            achievement.icon ? iconMap[achievement.icon] || <Trophy className="w-6 h-6" /> : <Trophy className="w-6 h-6" />
          ) : (
            <Lock className="w-5 h-5" />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <h4 className={`font-semibold ${unlocked ? 'text-amber-800' : 'text-gray-500'}`}>
            {achievement.name}
          </h4>
          <p className="text-sm text-gray-500 mt-1">{achievement.description}</p>
          {unlocked && (
            <p className="text-xs text-amber-600 mt-2">
              获得时间：{new Date(achievement.unlocked_at).toLocaleDateString('zh-CN')}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

interface AchievementGridProps {
  achievements: Achievement[]
  totalUnlocked: number
}

export function AchievementGrid({ achievements, totalUnlocked }: AchievementGridProps) {
  const allAchievements = [
    { id: 'first_blood', name: '初出茅庐', description: '完成第一个关卡', icon: '🎯' },
    { id: 'five_stars', name: '五关上将', description: '完成五个关卡', icon: '⭐' },
    { id: 'ten_completed', name: '十项全能', description: '完成十个关卡', icon: '🏆' },
    { id: 'perfectionist', name: '完美主义', description: '获得关卡满分', icon: '💯' },
    { id: 'speed_demon', name: '速度之星', description: '在时间限制内完成关卡', icon: '⚡' },
    { id: 'scholar', name: '学霸', description: '连续答对20道题', icon: '📚' }
  ]

  const unlockedIds = new Set(achievements.map(a => a.name))

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-gray-800">成就 ({totalUnlocked}/{allAchievements.length})</h3>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {allAchievements.map(achievement => {
          const unlockedAchievement = achievements.find(a => a.name === achievement.id)
          return (
            <AchievementCard
              key={achievement.id}
              achievement={{
                ...achievement,
                unlocked_at: unlockedAchievement?.unlocked_at || new Date().toISOString()
              }}
              unlocked={!!unlockedAchievement}
            />
          )
        })}
      </div>
    </div>
  )
}
