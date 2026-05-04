import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, MessageCircle } from 'lucide-react'

interface DialogueNode {
  id: string
  text: string
  emotion?: 'neutral' | 'happy' | 'sad' | 'angry' | 'surprised'
  actions?: Array<{ type: string; payload: Record<string, unknown> }>
  options?: DialogueOption[]
  next?: string
}

interface DialogueOption {
  text: string
  next: string
}

interface NPC {
  id: string
  name: string
  avatar?: string
  role: string
  dialogue_tree: DialogueNode[]
}

interface ChatMessage {
  id: string
  sender: 'npc' | 'user'
  content: string
  timestamp: Date
  emotion?: string
}

interface NPCChatProps {
  npc: NPC
  context?: Record<string, unknown>
  onComplete?: (data: Record<string, unknown>) => void
}

export default function NPCChat({ npc, context = {}, onComplete }: NPCChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputValue, setInputValue] = useState('')
  const [currentNodeId, setCurrentNodeId] = useState<string>(npc.dialogue_tree[0]?.id || '')
  const [isTyping, setIsTyping] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const currentNode = npc.dialogue_tree.find(node => node.id === currentNodeId)

  useEffect(() => {
    if (npc.dialogue_tree.length > 0 && messages.length === 0) {
      displayNode(npc.dialogue_tree[0])
    }
  }, [npc])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const displayNode = async (node: DialogueNode) => {
    setIsTyping(true)
    await new Promise(resolve => setTimeout(resolve, 1000))

    setMessages(prev => [...prev, {
      id: `npc-${node.id}-${Date.now()}`,
      sender: 'npc',
      content: node.text,
      timestamp: new Date(),
      emotion: node.emotion
    }])

    setIsTyping(false)

    if (node.actions) {
      node.actions.forEach(action => {
        if (action.type === 'grant_item') {
          console.log('Item granted:', action.payload)
        }
      })
    }
  }

  const handleOptionClick = async (option: DialogueOption) => {
    setMessages(prev => [...prev, {
      id: `user-${option.text}-${Date.now()}`,
      sender: 'user',
      content: option.text,
      timestamp: new Date()
    }])

    const nextNode = npc.dialogue_tree.find(node => node.id === option.next)
    if (nextNode) {
      setCurrentNodeId(nextNode.id)
      await displayNode(nextNode)
    }
  }

  const handleSend = async () => {
    if (!inputValue.trim()) return

    setMessages(prev => [...prev, {
      id: `user-${Date.now()}`,
      sender: 'user',
      content: inputValue,
      timestamp: new Date()
    }])

    const userMessage = inputValue
    setInputValue('')

    setIsTyping(true)
    await new Promise(resolve => setTimeout(resolve, 1500))

    const response = await generateAIResponse(userMessage, npc, context)

    setMessages(prev => [...prev, {
      id: `npc-ai-${Date.now()}`,
      sender: 'npc',
      content: response,
      timestamp: new Date()
    }])

    setIsTyping(false)
  }

  const generateAIResponse = async (userMessage: string, npc: NPC, context: Record<string, unknown>): Promise<string> => {
    const responses = [
      `让我来解释一下：${userMessage}涉及到我们培训的重要内容。`,
      `这是一个很好的问题！根据培训内容，${userMessage}的答案在于...`,
      `让我帮你分析一下这个问题。记住，关键是要理解核心概念。`,
      `不错的问题！${userMessage}在实践中非常重要，我来详细说明。`
    ]
    return responses[Math.floor(Math.random() * responses.length)]
  }

  const emotionEmoji: Record<string, string> = {
    neutral: '😐',
    happy: '😊',
    sad: '😢',
    angry: '😠',
    surprised: '😮'
  }

  return (
    <div className="flex flex-col h-[600px] bg-white rounded-xl shadow-lg overflow-hidden">
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 px-6 py-4">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 bg-white rounded-full flex items-center justify-center">
            <Bot className="w-7 h-7 text-blue-600" />
          </div>
          <div className="text-white">
            <h3 className="font-semibold">{npc.name}</h3>
            <p className="text-sm text-blue-100">{npc.role}</p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                message.sender === 'user'
                  ? 'bg-blue-600 text-white rounded-br-sm'
                  : 'bg-gray-100 text-gray-800 rounded-bl-sm'
              }`}
            >
              <div className="flex items-start gap-2">
                {message.sender === 'npc' && (
                  <Bot className="w-4 h-4 mt-1 text-gray-500" />
                )}
                <div>
                  <p className="whitespace-pre-wrap">{message.content}</p>
                  {message.emotion && (
                    <span className="text-xs opacity-70 ml-2">
                      {emotionEmoji[message.emotion]}
                    </span>
                  )}
                </div>
                {message.sender === 'user' && (
                  <User className="w-4 h-4 mt-1 text-blue-200" />
                )}
              </div>
            </div>
          </div>
        ))}

        {isTyping && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-2xl rounded-bl-sm px-4 py-3">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
              </div>
            </div>
          </div>
        )}

        {currentNode?.options && currentNode.options.length > 0 && !isTyping && (
          <div className="flex flex-wrap gap-2 mt-4">
            {currentNode.options.map((option, idx) => (
              <button
                key={idx}
                onClick={() => handleOptionClick(option)}
                className="px-4 py-2 bg-blue-50 text-blue-700 rounded-full hover:bg-blue-100 transition-colors text-sm"
              >
                {option.text}
              </button>
            ))}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="border-t p-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            placeholder="输入你的问题..."
            className="flex-1 px-4 py-2 border border-gray-300 rounded-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
          />
          <button
            onClick={handleSend}
            disabled={!inputValue.trim()}
            className="p-2 bg-blue-600 text-white rounded-full hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  )
}

export function createSampleNPC(): NPC {
  return {
    id: 'guide-npc-1',
    name: '小智导师',
    role: '培训导师',
    avatar: '/npc/guide.png',
    dialogue_tree: [
      {
        id: 'intro',
        text: '你好！我是你的培训导师小智。今天我们将学习重要的培训内容，准备好了吗？',
        emotion: 'happy',
        options: [
          { text: '准备好了！', next: 'topic1' },
          { text: '有什么奖励吗？', next: 'rewards' }
        ]
      },
      {
        id: 'rewards',
        text: '当然！完成培训后，你将获得经验值、金币和特殊成就。表现优秀还有机会获得稀有道具！',
        emotion: 'happy',
        next: 'topic1'
      },
      {
        id: 'topic1',
        text: '首先，让我们了解本次培训的核心知识点。请认真听讲，之后会有随堂测试。',
        emotion: 'neutral',
        options: [
          { text: '明白了', next: 'topic2' },
          { text: '可以举个例子吗？', next: 'example' }
        ]
      },
      {
        id: 'example',
        text: '当然！比如说在实际工作中，你需要按照规定流程操作设备。我们用射击游戏来模拟这个场景，让你身临其境地学习。',
        emotion: 'neutral',
        next: 'topic2'
      },
      {
        id: 'topic2',
        text: '很好！你已经掌握了基础知识。现在进入实战演练环节，证明你的实力吧！',
        emotion: 'happy',
        actions: [
          { type: 'unlock_level', payload: { level_id: 'practice-1' } }
        ]
      }
    ]
  }
}
