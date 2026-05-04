import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Play, Users, Clock, BookOpen, Bot, Target, Trophy, Star } from 'lucide-react'
import { courseAPI } from '../api'
import NPCChat, { createSampleNPC } from '../components/NPCChat'
import type { Course, Level, Question } from '../types'

export default function CourseDetail() {
  const { courseId } = useParams<{ courseId: string }>()
  const navigate = useNavigate()
  const [course, setCourse] = useState<Course | null>(null)
  const [levels, setLevels] = useState<Level[]>([])
  const [selectedLevel, setSelectedLevel] = useState<Level | null>(null)
  const [questions, setQuestions] = useState<Question[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'levels' | 'npc' | 'info'>('levels')
  const npc = createSampleNPC()

  useEffect(() => {
    fetchCourse()
  }, [courseId])

  useEffect(() => {
    if (selectedLevel) {
      fetchQuestions()
    }
  }, [selectedLevel])

  const fetchCourse = async () => {
    try {
      const id = parseInt(courseId || '1')
      const courses = await courseAPI.getCourses()
      const found = courses.find(c => c.id === id)
      if (found) {
        setCourse(found)
        const levelsData = await courseAPI.getLevels(id)
        setLevels(levelsData)
        if (levelsData.length > 0) {
          setSelectedLevel(levelsData[0])
        }
      }
    } catch (err) {
      console.error('Failed to fetch course:', err)
    } finally {
      setLoading(false)
    }
  }

  const fetchQuestions = async () => {
    if (!course || !selectedLevel) return
    try {
      const data = await courseAPI.getQuestions(course.id, selectedLevel.id)
      setQuestions(data)
    } catch (err) {
      console.error('Failed to fetch questions:', err)
    }
  }

  const handleStartLevel = (level: Level) => {
    navigate(`/game/${level.id}`)
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!course) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-800 mb-2">课程未找到</h2>
          <button onClick={() => navigate('/')} className="btn-primary">
            返回主页
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-gradient-to-r from-blue-600 to-purple-600 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 text-blue-100 hover:text-white mb-4 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
            返回课程列表
          </button>

          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-3xl font-bold mb-2">{course.name}</h1>
              <p className="text-blue-100 mb-4">{course.description}</p>
              <div className="flex items-center gap-6 text-sm text-blue-100">
                <div className="flex items-center gap-2">
                  <BookOpen className="w-4 h-4" />
                  <span>{levels.length} 个关卡</span>
                </div>
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4" />
                  <span>预计 2-3 小时</span>
                </div>
                <div className="flex items-center gap-2">
                  <Star className="w-4 h-4" />
                  <span>难度: 中级</span>
                </div>
              </div>
            </div>

            <button
              onClick={() => levels[0] && handleStartLevel(levels[0])}
              className="flex items-center gap-2 px-6 py-3 bg-white text-blue-600 rounded-xl font-semibold hover:bg-blue-50 transition-colors"
            >
              <Play className="w-5 h-5" />
              开始学习
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex gap-6">
          <div className="flex-1">
            <div className="bg-white rounded-xl shadow-sm overflow-hidden">
              <div className="border-b">
                <nav className="flex">
                  <button
                    onClick={() => setActiveTab('levels')}
                    className={`px-6 py-4 font-medium transition-colors ${
                      activeTab === 'levels'
                        ? 'text-blue-600 border-b-2 border-blue-600'
                        : 'text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <Target className="w-4 h-4" />
                      关卡列表
                    </div>
                  </button>
                  <button
                    onClick={() => setActiveTab('npc')}
                    className={`px-6 py-4 font-medium transition-colors ${
                      activeTab === 'npc'
                        ? 'text-blue-600 border-b-2 border-blue-600'
                        : 'text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <Bot className="w-4 h-4" />
                      AI 导师
                    </div>
                  </button>
                  <button
                    onClick={() => setActiveTab('info')}
                    className={`px-6 py-4 font-medium transition-colors ${
                      activeTab === 'info'
                        ? 'text-blue-600 border-b-2 border-blue-600'
                        : 'text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <Users className="w-4 h-4" />
                      课程信息
                    </div>
                  </button>
                </nav>
              </div>

              <div className="p-6">
                {activeTab === 'levels' && (
                  <div className="space-y-4">
                    {levels.map((level, index) => (
                      <div
                        key={level.id}
                        className={`p-4 rounded-xl border-2 transition-all cursor-pointer ${
                          selectedLevel?.id === level.id
                            ? 'border-blue-500 bg-blue-50'
                            : 'border-gray-200 hover:border-gray-300 bg-gray-50'
                        }`}
                        onClick={() => setSelectedLevel(level)}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-4">
                            <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                              selectedLevel?.id === level.id
                                ? 'bg-blue-600 text-white'
                                : 'bg-gray-200 text-gray-600'
                            }`}>
                              <span className="font-bold text-lg">{index + 1}</span>
                            </div>
                            <div>
                              <h3 className="font-semibold text-gray-800">{level.name}</h3>
                              <p className="text-sm text-gray-500">{level.description}</p>
                              <div className="flex items-center gap-4 mt-2 text-xs text-gray-400">
                                <span>满分: {level.max_score} 分</span>
                                <span>•</span>
                                <span>{questions.length} 题</span>
                              </div>
                            </div>
                          </div>
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              handleStartLevel(level)
                            }}
                            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                          >
                            <Play className="w-4 h-4" />
                            开始
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {activeTab === 'npc' && (
                  <NPCChat npc={npc} context={{ courseId: course.id }} />
                )}

                {activeTab === 'info' && (
                  <div className="space-y-6">
                    <div>
                      <h3 className="font-semibold text-gray-800 mb-3">课程介绍</h3>
                      <p className="text-gray-600 leading-relaxed">
                        {course.description || '本课程旨在帮助学员掌握核心知识和技能，通过游戏化闯关的方式，让学习变得更加有趣和有效。'}
                      </p>
                    </div>

                    <div>
                      <h3 className="font-semibold text-gray-800 mb-3">学习目标</h3>
                      <ul className="space-y-2">
                        <li className="flex items-center gap-2 text-gray-600">
                          <div className="w-2 h-2 bg-blue-500 rounded-full" />
                          掌握核心概念和原理
                        </li>
                        <li className="flex items-center gap-2 text-gray-600">
                          <div className="w-2 h-2 bg-blue-500 rounded-full" />
                          完成实战演练任务
                        </li>
                        <li className="flex items-center gap-2 text-gray-600">
                          <div className="w-2 h-2 bg-blue-500 rounded-full" />
                          通过全部关卡考核
                        </li>
                      </ul>
                    </div>

                    <div>
                      <h3 className="font-semibold text-gray-800 mb-3">课程特色</h3>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="p-4 bg-blue-50 rounded-lg">
                          <div className="flex items-center gap-2 text-blue-600 mb-2">
                            <Target className="w-5 h-5" />
                            <span className="font-medium">游戏化学习</span>
                          </div>
                          <p className="text-sm text-gray-600">3D沉浸式闯关体验</p>
                        </div>
                        <div className="p-4 bg-purple-50 rounded-lg">
                          <div className="flex items-center gap-2 text-purple-600 mb-2">
                            <Bot className="w-5 h-5" />
                            <span className="font-medium">AI导师</span>
                          </div>
                          <p className="text-sm text-gray-600">24小时智能答疑</p>
                        </div>
                        <div className="p-4 bg-green-50 rounded-lg">
                          <div className="flex items-center gap-2 text-green-600 mb-2">
                            <Trophy className="w-5 h-5" />
                            <span className="font-medium">成就系统</span>
                          </div>
                          <p className="text-sm text-gray-600">解锁成就获得奖励</p>
                        </div>
                        <div className="p-4 bg-amber-50 rounded-lg">
                          <div className="flex items-center gap-2 text-amber-600 mb-2">
                            <Users className="w-5 h-5" />
                            <span className="font-medium">互动学习</span>
                          </div>
                          <p className="text-sm text-gray-600">与NPC对话深入理解</p>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="w-80">
            <div className="bg-white rounded-xl shadow-sm p-6 sticky top-8">
              <h3 className="font-semibold text-gray-800 mb-4">学习进度</h3>
              <div className="mb-6">
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-gray-600">已完成</span>
                  <span className="font-medium text-blue-600">0 / {levels.length}</span>
                </div>
                <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div className="h-full bg-blue-500 rounded-full" style={{ width: '0%' }} />
                </div>
              </div>

              <h3 className="font-semibold text-gray-800 mb-4">当前关卡</h3>
              {selectedLevel && (
                <div className="p-4 bg-blue-50 rounded-lg">
                  <h4 className="font-medium text-gray-800">{selectedLevel.name}</h4>
                  <p className="text-sm text-gray-500 mt-1">{selectedLevel.description}</p>
                  <button
                    onClick={() => handleStartLevel(selectedLevel)}
                    className="w-full mt-4 btn-primary flex items-center justify-center gap-2"
                  >
                    <Play className="w-4 h-4" />
                    开始闯关
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
