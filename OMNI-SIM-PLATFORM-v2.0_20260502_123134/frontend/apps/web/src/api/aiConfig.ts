import { api } from './index'

export const aiConfigAPI = {
  getStatus: async () => {
    const response = await api.get('/ai-config/status')
    return response.data
  },

  updateConfig: async (config: {
    claude_api_key?: string
    qianwen_api_key?: string
    deepseek_api_key?: string
    default_model?: string
  }) => {
    const response = await api.post('/ai-config/update', config)
    return response.data
  },
}
