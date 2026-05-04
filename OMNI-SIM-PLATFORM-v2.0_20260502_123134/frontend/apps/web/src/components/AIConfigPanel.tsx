import React, { useState, useEffect } from 'react'
import { Brain, Key, CheckCircle, XCircle, Save } from 'lucide-react'
import { aiConfigAPI } from '../api/aiConfig'

interface AIConfigStatus {
  claude_api_key_configured: boolean
  qianwen_api_key_configured: boolean
  deepseek_api_key_configured: boolean
  default_model: string
  claude_model: string
  qianwen_model: string
  deepseek_model: string
}

export const AIConfigPanel: React.FC<{ onClose?: () => void }> = ({ onClose }) => {
  const [config, setConfig] = useState<AIConfigStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')

  const [claudeKey, setClaudeKey] = useState('')
  const [qianwenKey, setQianwenKey] = useState('')
  const [deepseekKey, setDeepseekKey] = useState('')
  const [defaultModel, setDefaultModel] = useState('claude')

  useEffect(() => {
    loadConfig()
  }, [])

  const loadConfig = async () => {
    try {
      const data = await aiConfigAPI.getStatus()
      setConfig(data)
      setDefaultModel(data.default_model)
    } catch (err) {
      console.error('Failed to load AI config:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    setMessage('')
    try {
      const result = await aiConfigAPI.updateConfig({
        claude_api_key: claudeKey || undefined,
        qianwen_api_key: qianwenKey || undefined,
        deepseek_api_key: deepseekKey || undefined,
        default_model: defaultModel,
      })
      setMessage(result.message || '配置已保存')
      if (onClose) onClose()
    } catch (err: any) {
      setMessage('保存失败: ' + (err.message || '未知错误'))
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="bg-white rounded-2xl shadow-lg p-6 max-w-2xl w-full">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-purple-100 rounded-xl">
            <Brain className="w-6 h-6 text-purple-600" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-gray-900">AI 配置</h2>
            <p className="text-sm text-gray-600">配置 AI API 密钥以启用智能功能</p>
          </div>
        </div>
        {onClose && (
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            ✕
          </button>
        )}
      </div>

      <div className="space-y-6">
        <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-xl p-4">
          <h3 className="font-semibold text-gray-900 mb-2">当前状态</h3>
          <div className="grid grid-cols-3 gap-4">
            <div className="flex items-center gap-2">
              {config?.claude_api_key_configured ? (
                <CheckCircle className="w-5 h-5 text-green-500" />
              ) : (
                <XCircle className="w-5 h-5 text-gray-400" />
              )}
              <span className="text-sm">Claude</span>
            </div>
            <div className="flex items-center gap-2">
              {config?.qianwen_api_key_configured ? (
                <CheckCircle className="w-5 h-5 text-green-500" />
              ) : (
                <XCircle className="w-5 h-5 text-gray-400" />
              )}
              <span className="text-sm">通义千问</span>
            </div>
            <div className="flex items-center gap-2">
              {config?.deepseek_api_key_configured ? (
                <CheckCircle className="w-5 h-5 text-green-500" />
              ) : (
                <XCircle className="w-5 h-5 text-gray-400" />
              )}
              <span className="text-sm">DeepSeek</span>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              <Key className="w-4 h-4 inline mr-1" />
              Claude API Key
            </label>
            <input
              type="password"
              value={claudeKey}
              onChange={(e) => setClaudeKey(e.target.value)}
              placeholder="sk-..." 
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            />
            <p className="text-xs text-gray-500 mt-1">当前模型: {config?.claude_model}</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              <Key className="w-4 h-4 inline mr-1" />
              通义千问 API Key
            </label>
            <input
              type="password"
              value={qianwenKey}
              onChange={(e) => setQianwenKey(e.target.value)}
              placeholder="sk-..." 
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            />
            <p className="text-xs text-gray-500 mt-1">当前模型: {config?.qianwen_model}</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              <Key className="w-4 h-4 inline mr-1" />
              DeepSeek API Key
            </label>
            <input
              type="password"
              value={deepseekKey}
              onChange={(e) => setDeepseekKey(e.target.value)}
              placeholder="sk-..." 
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            />
            <p className="text-xs text-gray-500 mt-1">当前模型: {config?.deepseek_model}</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              默认 AI 模型
            </label>
            <select
              value={defaultModel}
              onChange={(e) => setDefaultModel(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            >
              <option value="claude">Claude</option>
              <option value="qianwen">通义千问</option>
              <option value="deepseek">DeepSeek</option>
            </select>
          </div>
        </div>

        {message && (
          <div className={`p-3 rounded-lg ${message.includes('失败') ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'}`}>
            {message}
          </div>
        )}

        <div className="flex justify-end gap-3">
          {onClose && (
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
            >
              取消
            </button>
          )}
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 flex items-center gap-2"
          >
            {saving ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                保存中...
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                保存配置
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
