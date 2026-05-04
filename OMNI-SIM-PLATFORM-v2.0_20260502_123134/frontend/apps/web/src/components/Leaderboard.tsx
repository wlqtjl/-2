import { useState, useEffect } from 'react'
import { Trophy, Users, TrendingUp, Award } from 'lucide-react'
import { leaderboardAPI } from '../api'

interface LeaderboardEntry {
  rank: number
  user_id: number
  user_name: string
  score: number
  avatar?: string
}

interface LeaderboardProps {
  type?: 'global' | 'weekly' | 'monthly' | 'course' | 'achievement'
  courseId?: number
  limit?: number
  title?: string
  showUserRank?: boolean
}

export default function Leaderboard({
  type = 'global',
  courseId,
  limit = 10,
  title,
  showUserRank = true,
}: LeaderboardProps) {
  const [entries, setEntries] = useState<LeaderboardEntry[]>([])
  const [userRank, setUserRank] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState(type)

  const tabs = [
    { id: 'global', label: '全站', icon: <Users size={16} /> },
    { id: 'weekly', label: '本周', icon: <TrendingUp size={16} /> },
    { id: 'monthly', label: '本月', icon: <TrendingUp size={16} /> },
    { id: 'achievement', label: '成就', icon: <Award size={16} /> },
  ]

  useEffect(() => {
    fetchLeaderboard(activeTab)
  }, [activeTab, courseId, limit])

  const fetchLeaderboard = async (leaderboardType: string) => {
    try {
      setLoading(true)
      const data = await leaderboardAPI.getLeaderboard(leaderboardType, courseId, limit)
      setEntries(data.entries || [])
      
      if (showUserRank) {
        const rankData = await leaderboardAPI.getUserRank(leaderboardType, courseId)
        setUserRank(rankData.rank)
      }
    } catch (error) {
      console.error('Failed to fetch leaderboard:', error)
    } finally {
      setLoading(false)
    }
  }

  const getRankIcon = (rank: number) => {
    switch (rank) {
      case 1:
        return <Trophy className="w-6 h-6 text-yellow-500" />
      case 2:
        return <Trophy className="w-6 h-6 text-gray-400" />
      case 3:
        return <Trophy className="w-6 h-6 text-amber-600" />
      default:
        return <span className="text-gray-500 font-bold w-6 text-center">{rank}</span>
    }
  }

  const getRankColor = (rank: number) => {
    switch (rank) {
      case 1:
        return 'bg-gradient-to-r from-yellow-50 to-amber-50 border-yellow-200'
      case 2:
        return 'bg-gradient-to-r from-gray-50 to-slate-50 border-gray-200'
      case 3:
        return 'bg-gradient-to-r from-amber-50 to-orange-50 border-amber-200'
      default:
        return 'bg-white border-gray-100'
    }
  }

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      <div className="p-6 border-b border-gray-100">
        <h3 className="text-xl font-bold text-gray-800 mb-4 flex items-center gap-2">
          <Trophy className="w-6 h-6 text-yellow-500" />
          {title || '排行榜'}
        </h3>
        
        <div className="flex gap-2 bg-gray-50 p-1 rounded-xl">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === tab.id
                  ? 'bg-white text-blue-600 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div className="p-4">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <>
            {entries.length === 0 ? (
              <div className="text-center py-12">
                <Trophy className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                <p className="text-gray-500">暂无排行榜数据</p>
              </div>
            ) : (
              <div className="space-y-3">
                {entries.map((entry) => (
                  <div
                    key={entry.user_id}
                    className={`flex items-center gap-4 p-4 rounded-xl border transition-all hover:shadow-sm ${getRankColor(entry.rank)}`}
                  >
                    <div className="flex-shrink-0">
                      {getRankIcon(entry.rank)}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-gray-800 truncate">
                        {entry.user_name}
                      </p>
                    </div>
                    
                    <div className="flex-shrink-0">
                      <div className="flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-yellow-50 to-amber-50 rounded-full">
                        <Trophy className="w-4 h-4 text-yellow-500" />
                        <span className="font-bold text-yellow-700">{entry.score}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {showUserRank && userRank !== null && (
              <div className="mt-6 pt-4 border-t border-gray-100">
                <p className="text-sm text-gray-500 mb-2">您的排名</p>
                <div className="flex items-center gap-4 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl border border-blue-200">
                  <div className="flex-shrink-0 w-8 text-center">
                    <span className="text-2xl font-bold text-blue-600">#{userRank}</span>
                  </div>
                  
                  <div className="flex-1">
                    <p className="font-semibold text-gray-800">您</p>
                  </div>
                  
                  <div className="flex-shrink-0">
                    <div className="flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full">
                      <Trophy className="w-4 h-4 text-white" />
                      <span className="font-bold text-white">--</span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
