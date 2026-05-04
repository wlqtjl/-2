import axios from 'axios'
import type { User, Token, Course, Level, Question, LevelAttempt } from '../types'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  maxRedirects: 5,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      // 通过自定义事件通知应用层处理跳转，避免在 axios 拦截器里硬跳页面
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('auth:unauthorized'))
        if (window.location.pathname !== '/login') {
          window.location.replace('/login')
        }
      }
    }
    return Promise.reject(error)
  }
)

export const authAPI = {
  login: async (email: string, password: string): Promise<Token> => {
    const formData = new FormData()
    formData.append('username', email)
    formData.append('password', password)
    const response = await api.post('/auth/token', formData)
    return response.data
  },

  register: async (email: string, password: string, full_name?: string, role: string = 'learner'): Promise<User> => {
    const response = await api.post('/auth/register', { email, password, full_name, role })
    return response.data
  },

  me: async (): Promise<User> => {
    const response = await api.get('/auth/me')
    return response.data
  },
}

export const courseAPI = {
  getCourses: async (): Promise<Course[]> => {
    // Backend route is registered as /courses/ (with trailing slash).
    // Calling /courses may be swallowed by SPA fallback in same-origin deploy.
    const response = await api.get('/courses/')
    return response.data
  },

  getCourse: async (courseId: number): Promise<Course> => {
    const response = await api.get(`/courses/${courseId}`)
    return response.data
  },

  createCourse: async (name: string, description?: string): Promise<Course> => {
    const response = await api.post('/courses/', { name, description })
    return response.data
  },

  getLevels: async (courseId: number): Promise<Level[]> => {
    const response = await api.get(`/courses/${courseId}/levels`)
    return response.data
  },

  createLevel: async (courseId: number, name: string, description?: string): Promise<Level> => {
    const response = await api.post(`/courses/${courseId}/levels`, { name, description })
    return response.data
  },

  getQuestions: async (courseId: number, levelId: number): Promise<Question[]> => {
    const response = await api.get(`/courses/${courseId}/levels/${levelId}/questions`)
    return response.data
  },

  getLevelById: async (levelId: number): Promise<Level> => {
    const response = await api.get(`/courses/levels/${levelId}`)
    return response.data
  },

  getQuestionsByLevel: async (levelId: number): Promise<Question[]> => {
    const response = await api.get(`/courses/levels/${levelId}/questions`)
    return response.data
  },

  createQuestion: async (
    courseId: number,
    levelId: number,
    question: Omit<Question, 'id' | 'level_id' | 'created_at'>
  ): Promise<Question> => {
    const response = await api.post(`/courses/${courseId}/levels/${levelId}/questions`, question)
    return response.data
  },
}

export const attemptAPI = {
  start: async (levelId: number): Promise<LevelAttempt> => {
    const response = await api.post('/attempts/start', { level_id: levelId })
    return response.data
  },
  check: async (
    attemptId: number,
    questionId: number,
    answer: unknown,
  ): Promise<{ correct: boolean; points_awarded: number; explanation: string | null }> => {
    const response = await api.post('/attempts/check', {
      attempt_id: attemptId,
      question_id: questionId,
      answer,
    })
    return response.data
  },
  submit: async (attemptId: number, answers: Record<string, unknown>): Promise<LevelAttempt> => {
    const response = await api.post('/attempts/submit', { attempt_id: attemptId, answers })
    return response.data
  },
  getMyStats: async (): Promise<{ total_score: number; completed_levels: number; achievement_count: number }> => {
    const response = await api.get('/attempts/stats/me')
    return response.data
  },
}

export const contentAPI = {
  importContent: async (
    courseId: number,
    file: File,
    title?: string,
    description?: string
  ): Promise<{ job_id: string; status: string }> => {
    const formData = new FormData()
    formData.append('course_id', String(courseId))
    if (title) formData.append('title', title)
    if (description) formData.append('description', description)
    formData.append('file', file)
    const response = await api.post('/content/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  },

  getImportStatus: async (jobId: string): Promise<any> => {
    const response = await api.get(`/content/import/${jobId}/status`)
    return response.data
  },

  npcChat: async (message: string, context?: any): Promise<any> => {
    const response = await api.post('/content/npc/chat', { message, context })
    return response.data
  },

  getNPCHistory: async (): Promise<{ history: any[] }> => {
    const response = await api.get('/content/npc/history')
    return response.data
  },

  getAIStatus: async (): Promise<{ api_configured: boolean; coordinator_ready: boolean }> => {
    const response = await api.get('/content/ai/status')
    return response.data
  },
}

export const memoryAPI = {
  getUserProfile: async (): Promise<{ success: boolean; profile: any }> => {
    const response = await api.get('/memory/profile')
    return response.data
  },

  updateUserProfile: async (data: {
    learning_style?: string;
    difficulty_preference?: string;
    goal?: string;
    preferred_topics?: string[];
  }): Promise<{ success: boolean; message: string }> => {
    const response = await api.put('/memory/profile', data)
    return response.data
  },

  getMemoriesByType: async (memoryType: string, limit: number = 100): Promise<any> => {
    const response = await api.get(`/memory/type/${memoryType}`, { params: { limit } })
    return response.data
  },

  searchMemories: async (query: string, limit: number = 20): Promise<any> => {
    const response = await api.get('/memory/search', { params: { query, limit } })
    return response.data
  },

  recordLearningFeedback: async (data: {
    level_id: number;
    feedback_type: string;
    feedback_content: string;
    score?: number;
  }): Promise<any> => {
    const response = await api.post('/memory/feedback', data)
    return response.data
  },

  getLearningInsights: async (): Promise<{ success: boolean; insights: any }> => {
    const response = await api.get('/memory/insights')
    return response.data
  },
}

export const levelEngineAPI = {
  startLevel: async (courseId: number, levelId: number): Promise<any> => {
    const response = await api.post('/levels/engine/start', null, {
      params: { course_id: courseId, level_id: levelId },
    })
    return response.data
  },

  getSession: async (sessionId: string): Promise<any> => {
    const response = await api.get(`/levels/engine/session/${sessionId}`)
    return response.data
  },

  answerTask: async (sessionId: string, userAnswer: any, taskIndex?: number): Promise<any> => {
    const response = await api.post(`/levels/engine/session/${sessionId}/answer`, userAnswer, {
      params: { task_index: taskIndex },
    })
    return response.data
  },

  nextTask: async (sessionId: string): Promise<any> => {
    const response = await api.post(`/levels/engine/session/${sessionId}/next`)
    return response.data
  },

  pauseLevel: async (sessionId: string): Promise<any> => {
    const response = await api.post(`/levels/engine/session/${sessionId}/pause`)
    return response.data
  },

  resumeLevel: async (sessionId: string): Promise<any> => {
    const response = await api.post(`/levels/engine/session/${sessionId}/resume`)
    return response.data
  },
}

export const leaderboardAPI = {
  getLeaderboard: async (leaderboardType: string, courseId?: number, limit?: number): Promise<any> => {
    const response = await api.get(`/leaderboard/${leaderboardType}`, {
      params: { course_id: courseId, limit },
    })
    return response.data
  },

  getUserRank: async (leaderboardType: string, courseId?: number): Promise<any> => {
    const response = await api.get(`/leaderboard/${leaderboardType}/rank`, {
      params: { course_id: courseId },
    })
    return response.data
  },

  getUserSurrounding: async (leaderboardType: string, rangeSize?: number, courseId?: number): Promise<any> => {
    const response = await api.get(`/leaderboard/${leaderboardType}/surrounding`, {
      params: { range_size: rangeSize, course_id: courseId },
    })
    return response.data
  },

  updateScore: async (leaderboardType: string, score: number, courseId?: number): Promise<any> => {
    const response = await api.post(`/leaderboard/${leaderboardType}/score`, null, {
      params: { score, course_id: courseId },
    })
    return response.data
  },
}

export const getCourses = courseAPI.getCourses
export const getCourse = courseAPI.getCourse
export const createCourse = courseAPI.createCourse
export const getLevels = courseAPI.getLevels
export const getQuestions = courseAPI.getQuestions

export const adminAPI = {
  getDashboardStats: async (): Promise<any> => {
    const response = await api.get('/admin/dashboard/stats')
    return response.data
  },

  getUsers: async (params: { page?: number; page_size?: number; role?: string; search?: string } = {}): Promise<any> => {
    const response = await api.get('/admin/users', { params })
    return response.data
  },

  updateUser: async (userId: number, data: { role?: string; is_active?: boolean }): Promise<any> => {
    const response = await api.put(`/admin/users/${userId}`, null, { params: data })
    return response.data
  },

  deleteUser: async (userId: number): Promise<any> => {
    const response = await api.delete(`/admin/users/${userId}`)
    return response.data
  },

  getCourses: async (params: { page?: number; page_size?: number; status?: string; search?: string } = {}): Promise<any> => {
    const response = await api.get('/admin/courses', { params })
    return response.data
  },

  createCourse: async (name: string, description?: string): Promise<any> => {
    const response = await api.post('/admin/courses', null, { params: { name, description } })
    return response.data
  },

  updateCourse: async (courseId: number, data: { name?: string; description?: string; status?: string }): Promise<any> => {
    const response = await api.put(`/admin/courses/${courseId}`, null, { params: data })
    return response.data
  },

  deleteCourse: async (courseId: number): Promise<any> => {
    const response = await api.delete(`/admin/courses/${courseId}`)
    return response.data
  },

  getCourseLevels: async (courseId: number): Promise<any> => {
    const response = await api.get(`/admin/courses/${courseId}/levels`)
    return response.data
  },

  createLevel: async (courseId: number, name: string, description?: string): Promise<any> => {
    const response = await api.post(`/admin/courses/${courseId}/levels`, null, { params: { name, description } })
    return response.data
  },

  deleteLevel: async (levelId: number): Promise<any> => {
    const response = await api.delete(`/admin/levels/${levelId}`)
    return response.data
  },

  getAnalyticsSummary: async (days: number = 30): Promise<any> => {
    const response = await api.get('/admin/analytics/summary', { params: { days } })
    return response.data
  },

  getUserProgressStats: async (): Promise<any> => {
    const response = await api.get('/admin/analytics/user-progress')
    return response.data
  },

  getAchievementsStats: async (): Promise<any> => {
    const response = await api.get('/admin/achievements')
    return response.data
  },

  getSystemHealth: async (): Promise<any> => {
    const response = await api.get('/admin/system/health')
    return response.data
  },
}

// ── 场景包 DSL v1 ──────────────────────────────────────────────────────────────
export const scenarioAPI = {
  list: async (includeDrafts = false): Promise<any[]> => {
    const response = await api.get('/api/scenarios', { params: { include_drafts: includeDrafts } })
    return response.data
  },

  get: async (scenarioId: string): Promise<any> => {
    const response = await api.get(`/api/scenarios/${scenarioId}`)
    return response.data
  },

  create: async (data: {
    scenario_id: string
    name: string
    domain?: string
    difficulty?: string
    version?: string
    status?: string
    payload: object
  }): Promise<any> => {
    const response = await api.post('/api/scenarios', data)
    return response.data
  },

  update: async (scenarioId: string, data: {
    name?: string
    domain?: string
    difficulty?: string
    version?: string
    status?: string
    payload?: object
  }): Promise<any> => {
    const response = await api.put(`/api/scenarios/${scenarioId}`, data)
    return response.data
  },
}

export { api }
export default api
