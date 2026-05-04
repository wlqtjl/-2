export interface User {
  id: number
  email: string
  full_name: string | null
  role: string
  is_active: boolean
  created_at: string
}

export interface Token {
  access_token: string
  token_type: string
}

export interface Course {
  id: number
  name: string
  description: string | null
  tenant_id: number
  status: string
  created_at: string
  updated_at: string
}

export interface Level {
  id: number
  name: string
  description: string | null
  order: number
  max_score: number
  config: object | null
  course_id: number
  created_at: string
  updated_at: string
}

export interface Question {
  id: number
  type: string
  content: string
  options: string[] | null
  correct_answer: object
  explanation: string | null
  difficulty: number
  level_id: number
  created_at: string
}

export interface LevelAttempt {
  id: number
  user_id: number
  level_id: number
  score: number
  max_score: number
  completed: boolean
  started_at: string
  completed_at: string | null
}

export interface Achievement {
  id: number
  name: string
  description: string | null
  icon: string | null
  unlocked_at: string
}

export interface LearnerProfile {
  id: number
  user_id: number
  memory_type: string
  data: Record<string, unknown>
  last_updated: string
}
