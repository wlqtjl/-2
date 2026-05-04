import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Target, Trophy, Clock, Glasses, Crosshair } from 'lucide-react'
import GameScene from '../components/GameScene'
import { courseAPI } from '../api'
import type { Question } from '../types'

// Backend origin (FastAPI) — the V2V FPS game is mounted there at /game/.
const BACKEND_BASE = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000'

export default function Game() {
  const { levelId } = useParams<{ levelId: string }>()
  const navigate = useNavigate()
  const [questions, setQuestions] = useState<Question[]>([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [score, setScore] = useState(0)
  const [timeElapsed, setTimeElapsed] = useState(0)
  const [isComplete, setIsComplete] = useState(false)
  const [answers, setAnswers] = useState<Record<string, unknown>>({})
  const [showFeedback, setShowFeedback] = useState(false)
  const [isCorrect, setIsCorrect] = useState(false)
  const [enableVR, setEnableVR] = useState(false)
  // 默认走 FPS 通关体验：每个关卡都以 V2V 战役为主入口；
  // 用户可以切到“题目模式”做传统答题。
  const [enableFPS, setEnableFPS] = useState(true)
  const [fpsResult, setFpsResult] = useState<null | { passed: boolean; score: number; attemptId?: number }>(null)

  useEffect(() => {
    fetchQuestions()
  }, [levelId])

  // 监听游戏 iframe 的通关消息：写入 LevelAttempt 后展示结算。
  useEffect(() => {
    const onMsg = (ev: MessageEvent) => {
      const data = ev.data || {}
      if (data && data.type === 'omni-level-complete') {
        const resp = data.response || {}
        setFpsResult({
          passed: !!resp.passed,
          score: data.score | 0,
          attemptId: resp.attemptId,
        })
        setIsComplete(true)
      }
    }
    window.addEventListener('message', onMsg)
    return () => window.removeEventListener('message', onMsg)
  }, [])

  useEffect(() => {
    if (!isComplete) {
      const timer = setInterval(() => {
        setTimeElapsed((prev) => prev + 1)
      }, 1000)
      return () => clearInterval(timer)
    }
  }, [isComplete])

  const fetchQuestions = async () => {
    try {
      const data = await courseAPI.getQuestions(1, parseInt(levelId || '1'))
      setQuestions(data)
    } catch (err) {
      console.error('Failed to fetch questions:', err)
    }
  }

  const handleAnswer = (answer: unknown) => {
    const currentQuestion = questions[currentIndex]
    const userAnswer = answer
    
    setAnswers((prev) => ({ ...prev, [currentQuestion.id]: userAnswer }))
    
    const correct = JSON.stringify(userAnswer) === JSON.stringify(currentQuestion.correct_answer)
    setIsCorrect(correct)
    
    if (correct) {
      setScore((prev) => prev + Math.floor(currentQuestion.max_score || 100))
    }
    
    setShowFeedback(true)
  }

  const handleNext = () => {
    setShowFeedback(false)
    if (currentIndex < questions.length - 1) {
      setCurrentIndex((prev) => prev + 1)
    } else {
      setIsComplete(true)
    }
  }

  const handleBack = () => {
    navigate('/')
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  const currentQuestion = questions[currentIndex]

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <button
            onClick={handleBack}
            className="flex items-center gap-2 text-gray-300 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
            返回
          </button>
          <div className="flex items-center gap-6">
            <button
              onClick={() => setEnableFPS((v) => !v)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all ${
                enableFPS
                  ? 'bg-emerald-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
              title="启动 V2V 迁移 FPS 战役"
            >
              <Crosshair className="w-5 h-5" />
              {enableFPS ? 'FPS已启用' : 'FPS战役'}
            </button>
            <button
              onClick={() => setEnableVR(!enableVR)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all ${
                enableVR
                  ? 'bg-purple-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              <Glasses className="w-5 h-5" />
              {enableVR ? 'VR已启用' : 'VR模式'}
            </button>
            <div className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-blue-400" />
              <span>{formatTime(timeElapsed)}</span>
            </div>
            <div className="flex items-center gap-2">
              <Trophy className="w-5 h-5 text-amber-400" />
              <span>{score} 分</span>
            </div>
            <div className="flex items-center gap-2">
              <Target className="w-5 h-5 text-green-400" />
              <span>{currentIndex + 1} / {questions.length}</span>
            </div>
          </div>
        </div>
      </header>

      <main className={enableFPS || enableVR ? 'h-screen' : 'flex'}>
        {enableFPS ? (
          fpsResult ? (
            <div className="flex flex-col items-center justify-center h-full bg-gradient-to-br from-slate-900 via-emerald-950 to-slate-900">
              <div className="max-w-md w-full bg-slate-800/80 border border-emerald-500/30 rounded-2xl p-10 shadow-2xl text-center">
                <div className={`w-24 h-24 mx-auto rounded-full flex items-center justify-center mb-6 ${fpsResult.passed ? 'bg-emerald-500' : 'bg-amber-500'}`}>
                  <Trophy className="w-12 h-12 text-white" />
                </div>
                <h2 className="text-3xl font-bold text-white mb-2">{fpsResult.passed ? '关卡通关！' : '本次未达标'}</h2>
                <p className="text-lg text-emerald-300 mb-1">迁移得分：<span className="font-bold">{fpsResult.score}</span></p>
                {fpsResult.attemptId && (
                  <p className="text-xs text-slate-400 mb-6">通关记录 #{fpsResult.attemptId} 已计入学习档案</p>
                )}
                {!fpsResult.attemptId && <p className="mb-6" />}
                <div className="flex gap-3 justify-center">
                  <button onClick={() => { setFpsResult(null); setIsComplete(false); }} className="px-5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg">再来一次</button>
                  <button onClick={handleBack} className="px-5 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg">返回主页</button>
                </div>
              </div>
            </div>
          ) : (
            <iframe
              title="V2V Migration FPS"
              src={`${BACKEND_BASE}/game/index.html?token=${encodeURIComponent(
                localStorage.getItem('token') || '',
              )}&levelId=${encodeURIComponent(levelId || '')}`}
              className="w-full h-full border-0"
              allow="fullscreen; gamepad; xr-spatial-tracking"
            />
          )
        ) : (
          <>
            {!enableVR && (
          <div className="w-1/3 bg-gray-800 p-6">
            {isComplete ? (
              <div className="text-center py-12">
                <div className="w-24 h-24 bg-amber-500 rounded-full flex items-center justify-center mx-auto mb-6">
                  <Trophy className="w-12 h-12 text-white" />
                </div>
                <h2 className="text-2xl font-bold mb-2">关卡完成!</h2>
                <p className="text-xl text-amber-400 mb-4">得分: {score}</p>
                <button onClick={handleBack} className="btn-primary">
                  返回主页
                </button>
              </div>
            ) : currentQuestion ? (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-semibold mb-2">问题 {currentIndex + 1}</h3>
                  <p className="text-gray-300">{currentQuestion.content}</p>
                </div>

                {currentQuestion.type === 'single_choice' && currentQuestion.options && (
                  <div className="space-y-2">
                    {currentQuestion.options.map((option, idx) => (
                      <button
                        key={idx}
                        onClick={() => !showFeedback && handleAnswer(option)}
                        disabled={showFeedback}
                        className={`w-full p-4 rounded-lg text-left transition-all ${
                          showFeedback
                            ? JSON.stringify(option) === JSON.stringify(currentQuestion.correct_answer)
                              ? 'bg-green-600 border-green-500'
                              : answers[currentQuestion.id] === option && !isCorrect
                              ? 'bg-red-600 border-red-500'
                              : 'bg-gray-700 opacity-50'
                            : 'bg-gray-700 hover:bg-gray-600 border-gray-600'
                        } border`}
                      >
                        {String.fromCharCode(65 + idx)}. {option}
                      </button>
                    ))}
                  </div>
                )}

                {currentQuestion.type === 'true_false' && (
                  <div className="grid grid-cols-2 gap-3">
                    <button
                      onClick={() => !showFeedback && handleAnswer(true)}
                      disabled={showFeedback}
                      className={`p-4 rounded-lg transition-all ${
                        showFeedback
                          ? currentQuestion.correct_answer === true
                            ? 'bg-green-600'
                            : answers[currentQuestion.id] === true && !isCorrect
                            ? 'bg-red-600'
                            : 'bg-gray-700 opacity-50'
                          : 'bg-green-700 hover:bg-green-600'
                      }`}
                    >
                      ✓ 正确
                    </button>
                    <button
                      onClick={() => !showFeedback && handleAnswer(false)}
                      disabled={showFeedback}
                      className={`p-4 rounded-lg transition-all ${
                        showFeedback
                          ? currentQuestion.correct_answer === false
                            ? 'bg-green-600'
                            : answers[currentQuestion.id] === false && !isCorrect
                            ? 'bg-red-600'
                            : 'bg-gray-700 opacity-50'
                          : 'bg-red-700 hover:bg-red-600'
                      }`}
                    >
                      ✗ 错误
                    </button>
                  </div>
                )}

                {showFeedback && (
                  <div className={`p-4 rounded-lg ${isCorrect ? 'bg-green-900' : 'bg-red-900'}`}>
                    <p className="font-semibold mb-2">{isCorrect ? '回答正确!' : '回答错误'}</p>
                    {currentQuestion.explanation && (
                      <p className="text-sm text-gray-300">{currentQuestion.explanation}</p>
                    )}
                    <button
                      onClick={handleNext}
                      className="mt-4 btn-primary w-full"
                    >
                      {currentIndex < questions.length - 1 ? '下一题' : '完成关卡'}
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-12">
                <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
                <p>加载中...</p>
              </div>
            )}
          </div>
        )}

        <div className={enableVR ? 'h-full' : 'w-2/3'}>
          <GameScene 
            questionIndex={currentIndex} 
            isCorrect={isCorrect}
            showFeedback={showFeedback}
            enableVR={enableVR}
          />
        </div>
          </>
        )}
      </main>
    </div>
  )
}
