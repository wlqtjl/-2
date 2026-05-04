import { useState, useCallback, useRef } from 'react'
import { Plus, Trash2, Save, Play, GripVertical, ChevronDown, ChevronRight, MessageSquare, Sparkles, Wand2, Target, Zap, Bot, Eye, RotateCcw, Copy, Check } from 'lucide-react'
import { createLevelTemplate, createTaskTemplate, validateLevelDSL } from './LevelDSL'

interface LevelEditorProps {
  levelId?: string
  initialData?: object
  onSave: (data: object) => void
  onPreview: (data: object) => void
}

interface TaskEditorProps {
  task: Record<string, unknown>
  index: number
  onUpdate: (index: number, task: Record<string, unknown>) => void
  onDelete: (index: number) => void
  onMoveUp: (index: number) => void
  onMoveDown: (index: number) => void
  totalTasks: number
}

interface NPCDialogue {
  id: string
  npcName: string
  message: string
  trigger: 'start' | 'correct' | 'wrong' | 'timed'
  responses?: string[]
  nextDialogueId?: string
}

interface SceneElement {
  id: string
  type: 'target' | 'enemy' | 'obstacle' | 'powerup' | 'collectible'
  position: { x: number; y: number; z: number }
  points?: number
  name?: string
}

interface DialogueNode {
  id: string
  text: string
  responses: { text: string; nextId?: string }[]
  type: 'start' | 'normal' | 'end'
  position: { x: number; y: number }
}

function TaskEditor({ task, index, onUpdate, onDelete, onMoveUp, onMoveDown, totalTasks }: TaskEditorProps) {
  const [expanded, setExpanded] = useState(true)
  const [copied, setCopied] = useState(false)

  const questionTypes = [
    { value: 'single_choice', label: '单选题', icon: 'circle' },
    { value: 'multiple_choice', label: '多选题', icon: 'check-square' },
    { value: 'true_false', label: '判断题', icon: 'toggle-left' },
    { value: 'fill_blank', label: '填空题', icon: 'text-cursor' },
    { value: 'shooting', label: '射击题', icon: 'crosshair' },
    { value: 'drag_drop', label: '拖拽题', icon: 'move' }
  ]

  const handleCopy = () => {
    const newTask = { ...task, id: `task-${Date.now()}` }
    onUpdate(index, newTask)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden shadow-sm hover:shadow-md transition-shadow">
      <div
        className="flex items-center justify-between p-3 bg-gradient-to-r from-gray-50 to-gray-100 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1">
            <button
              onClick={(e) => {
                e.stopPropagation()
                onMoveUp(index)
              }}
              disabled={index === 0}
              className="p-1 text-gray-400 hover:text-gray-600 hover:bg-white/50 rounded disabled:opacity-30"
            >
              <ChevronDown className="w-4 h-4 rotate-180" />
            </button>
            <GripVertical className="w-5 h-5 text-gray-400 cursor-grab" />
            <button
              onClick={(e) => {
                e.stopPropagation()
                onMoveDown(index)
              }}
              disabled={index === totalTasks - 1}
              className="p-1 text-gray-400 hover:text-gray-600 hover:bg-white/50 rounded disabled:opacity-30"
            >
              <ChevronDown className="w-4 h-4" />
            </button>
          </div>
          <span className="font-medium text-gray-700">任务 #{index + 1}</span>
          <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded-full">
            {questionTypes.find(t => t.value === task.type)?.label || task.type}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={(e) => {
              e.stopPropagation()
              handleCopy()
            }}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-white/50 rounded"
            title="复制任务"
          >
            {copied ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation()
              onDelete(index)
            }}
            className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded"
            title="删除任务"
          >
            <Trash2 className="w-4 h-4" />
          </button>
          {expanded ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}
        </div>
      </div>

      {expanded && (
        <div className="p-4 space-y-4 bg-white">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">题目类型</label>
              <select
                value={task.type as string}
                onChange={(e) => onUpdate(index, { ...task, type: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
              >
                {questionTypes.map((type) => (
                  <option key={type.value} value={type.value}>{type.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">难度</label>
              <select
                value={task.difficulty as number || 1}
                onChange={(e) => onUpdate(index, { ...task, difficulty: parseInt(e.target.value) })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
              >
                <option value={1}>简单</option>
                <option value={2}>中等</option>
                <option value={3}>困难</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">分值</label>
              <input
                type="number"
                value={task.points as number || 10}
                onChange={(e) => onUpdate(index, { ...task, points: parseInt(e.target.value) })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                min="1"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">题目内容</label>
            <textarea
              value={task.content as string}
              onChange={(e) => onUpdate(index, { ...task, content: e.target.value })}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
              placeholder="请输入题目内容..."
            />
          </div>

          {(task.type === 'single_choice' || task.type === 'multiple_choice') && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">选项</label>
              <div className="space-y-2">
                {((task.options as string[]) || []).map((option, optIdx) => (
                  <div key={optIdx} className="flex items-center gap-2">
                    <span className="text-gray-500 w-6 font-medium">{String.fromCharCode(65 + optIdx)}.</span>
                    <input
                      type="text"
                      value={option}
                      onChange={(e) => {
                        const newOptions = [...((task.options as string[]) || [])]
                        newOptions[optIdx] = e.target.value
                        onUpdate(index, { ...task, options: newOptions })
                      }}
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                    {task.type === 'multiple_choice' ? (
                      <button
                        onClick={() => {
                          const currentAnswer = (task.correct_answer as string[]) || []
                          const optionLabel = String.fromCharCode(65 + optIdx)
                          const newAnswer = currentAnswer.includes(optionLabel)
                            ? currentAnswer.filter(a => a !== optionLabel)
                            : [...currentAnswer, optionLabel].sort()
                          onUpdate(index, { ...task, correct_answer: newAnswer })
                        }}
                        className={`px-2 py-1 rounded text-xs font-medium ${
                          ((task.correct_answer as string[]) || []).includes(String.fromCharCode(65 + optIdx))
                            ? 'bg-green-500 text-white'
                            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                        }`}
                      >
                        正确
                      </button>
                    ) : (
                      <button
                        onClick={() => onUpdate(index, { ...task, correct_answer: String.fromCharCode(65 + optIdx) })}
                        className={`px-2 py-1 rounded text-xs font-medium ${
                          task.correct_answer === String.fromCharCode(65 + optIdx)
                            ? 'bg-green-500 text-white'
                            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                        }`}
                      >
                        正确
                      </button>
                    )}
                    <button
                      onClick={() => {
                        const newOptions = [...((task.options as string[]) || [])]
                        newOptions.splice(optIdx, 1)
                        onUpdate(index, { ...task, options: newOptions })
                      }}
                      className="p-2 text-red-500 hover:bg-red-50 rounded"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
              <button
                onClick={() => {
                  const newOptions = [...((task.options as string[]) || []), `选项 ${String.fromCharCode(65 + ((task.options as string[]) || []).length)}`]
                  onUpdate(index, { ...task, options: newOptions })
                }}
                className="mt-2 flex items-center gap-1 text-blue-600 hover:text-blue-700 text-sm"
              >
                <Plus className="w-4 h-4" /> 添加选项
              </button>
            </div>
          )}

          {task.type === 'true_false' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">正确答案</label>
              <div className="flex gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    checked={task.correct_answer === true}
                    onChange={() => onUpdate(index, { ...task, correct_answer: true })}
                    className="text-blue-600"
                  />
                  <span className="text-gray-700">正确</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    checked={task.correct_answer === false}
                    onChange={() => onUpdate(index, { ...task, correct_answer: false })}
                    className="text-blue-600"
                  />
                  <span className="text-gray-700">错误</span>
                </label>
              </div>
            </div>
          )}

          {task.type === 'fill_blank' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">正确答案</label>
              <input
                type="text"
                value={task.correct_answer as string || ''}
                onChange={(e) => onUpdate(index, { ...task, correct_answer: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="请输入正确答案..."
              />
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">提示（可选）</label>
            <input
              type="text"
              value={(task.hint as string) || ''}
              onChange={(e) => onUpdate(index, { ...task, hint: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="给玩家的提示..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">解析说明（可选）</label>
            <textarea
              value={(task.explanation as string) || ''}
              onChange={(e) => onUpdate(index, { ...task, explanation: e.target.value })}
              rows={2}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
              placeholder="题目解析..."
            />
          </div>

          <div className="flex items-center justify-between pt-2 border-t border-gray-100">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={task.required !== false}
                onChange={(e) => onUpdate(index, { ...task, required: e.target.checked })}
                className="text-blue-600 rounded"
              />
              <span className="text-sm text-gray-600">必须完成</span>
            </label>
          </div>
        </div>
      )}
    </div>
  )
}

const NPCDialogueTreeEditor = ({ dialogues, onUpdate }: { dialogues: DialogueNode[], onUpdate: (dialogues: DialogueNode[]) => void }) => {
  const canvasRef = useRef<HTMLDivElement>(null)
  const [selectedNode, setSelectedNode] = useState<string | null>(null)
  const [dragging, setDragging] = useState<string | null>(null)
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 })

  const addNode = (type: 'normal' | 'end' = 'normal') => {
    const newNode: DialogueNode = {
      id: `node-${Date.now()}`,
      text: type === 'end' ? '对话结束' : '新对话节点',
      responses: type === 'end' ? [] : [{ text: '继续', nextId: undefined }],
      type: dialogues.length === 0 ? 'start' : type,
      position: { x: 100 + dialogues.length * 150, y: 100 + (dialogues.length % 3) * 100 }
    }
    onUpdate([...dialogues, newNode])
  }

  const updateNode = (id: string, updates: Partial<DialogueNode>) => {
    onUpdate(dialogues.map(node => node.id === id ? { ...node, ...updates } : node))
  }

  const deleteNode = (id: string) => {
    const newDialogues = dialogues.filter(node => node.id !== id)
    onUpdate(newDialogues.map(node => ({
      ...node,
      responses: node.responses.map(r => ({
        ...r,
        nextId: r.nextId === id ? undefined : r.nextId
      }))
    })))
    if (selectedNode === id) setSelectedNode(null)
  }

  const addResponse = (nodeId: string) => {
    onUpdate(dialogues.map(node =>
      node.id === nodeId
        ? { ...node, responses: [...node.responses, { text: '新选项', nextId: undefined }] }
        : node
    ))
  }

  const updateResponse = (nodeId: string, responseIndex: number, updates: { text?: string; nextId?: string }) => {
    onUpdate(dialogues.map(node =>
      node.id === nodeId
        ? {
            ...node,
            responses: node.responses.map((r, i) =>
              i === responseIndex ? { ...r, ...updates } : r
            )
          }
        : node
    ))
  }

  const deleteResponse = (nodeId: string, responseIndex: number) => {
    onUpdate(dialogues.map(node =>
      node.id === nodeId
        ? { ...node, responses: node.responses.filter((_, i) => i !== responseIndex) }
        : node
    ))
  }

  const handleMouseDown = (e: React.MouseEvent, nodeId: string) => {
    const node = dialogues.find(n => n.id === nodeId)
    if (!node || !canvasRef.current) return
    
    const rect = canvasRef.current.getBoundingClientRect()
    setDragOffset({
      x: e.clientX - rect.left - node.position.x,
      y: e.clientY - rect.top - node.position.y
    })
    setDragging(nodeId)
    setSelectedNode(nodeId)
    e.preventDefault()
  }

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!dragging || !canvasRef.current) return
    
    const rect = canvasRef.current.getBoundingClientRect()
    const x = Math.max(0, Math.min(rect.width - 180, e.clientX - rect.left - dragOffset.x))
    const y = Math.max(0, Math.min(rect.height - 80, e.clientY - rect.top - dragOffset.y))
    
    updateNode(dragging, { position: { x, y } })
  }

  const handleMouseUp = () => {
    setDragging(null)
  }

  const nodeColors = {
    start: 'bg-gradient-to-br from-green-500 to-green-600 text-white',
    normal: 'bg-gradient-to-br from-blue-500 to-blue-600 text-white',
    end: 'bg-gradient-to-br from-gray-500 to-gray-600 text-white'
  }

  return (
    <div className="bg-white rounded-xl p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
          <MessageSquare className="w-5 h-5" />
          NPC 对话树编辑器
        </h2>
        <div className="flex gap-2">
          <button
            onClick={() => addNode('normal')}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            <Plus className="w-4 h-4" />
            添加节点
          </button>
          <button
            onClick={() => addNode('end')}
            className="flex items-center gap-2 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
          >
            <Plus className="w-4 h-4" />
            结束节点
          </button>
        </div>
      </div>

      <div className="relative border border-gray-200 rounded-lg overflow-hidden">
        <div
          ref={canvasRef}
          className="h-96 bg-gradient-to-br from-gray-50 to-gray-100 relative"
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
        >
          <svg className="absolute inset-0 w-full h-full pointer-events-none">
            {dialogues.flatMap(node =>
              node.responses
                .filter(r => r.nextId)
                .map(response => {
                  const targetNode = dialogues.find(n => n.id === response.nextId)
                  if (!targetNode) return null
                  return (
                    <line
                      key={`${node.id}-${response.nextId}`}
                      x1={node.position.x + 90}
                      y1={node.position.y + 40}
                      x2={targetNode.position.x}
                      y2={targetNode.position.y + 40}
                      stroke="#94a3b8"
                      strokeWidth="2"
                      markerEnd="url(#arrowhead)"
                    />
                  )
                })
            )}
            <defs>
              <marker
                id="arrowhead"
                markerWidth="10"
                markerHeight="7"
                refX="9"
                refY="3.5"
                orient="auto"
              >
                <polygon points="0 0, 10 3.5, 0 7" fill="#94a3b8" />
              </marker>
            </defs>
          </svg>

          {dialogues.map(node => (
            <div
              key={node.id}
              className={`absolute cursor-move select-none ${nodeColors[node.type]} rounded-lg shadow-lg p-3 min-w-[180px] ${dragging === node.id ? 'ring-2 ring-yellow-400' : ''} ${selectedNode === node.id ? 'ring-2 ring-white' : ''}`}
              style={{
                left: node.position.x,
                top: node.position.y
              }}
              onMouseDown={(e) => handleMouseDown(e, node.id)}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium opacity-80">
                  {node.type === 'start' ? '开始' : node.type === 'end' ? '结束' : '对话'}
                </span>
                {node.type !== 'start' && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      deleteNode(node.id)
                    }}
                    className="text-white/60 hover:text-white"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
              <textarea
                value={node.text}
                onChange={(e) => updateNode(node.id, { text: e.target.value })}
                className="w-full bg-white/20 text-white border-none rounded resize-none text-sm"
                rows={2}
                onClick={(e) => e.stopPropagation()}
              />
              {node.type !== 'end' && (
                <div className="mt-2 space-y-1">
                  {node.responses.map((response, idx) => (
                    <div key={idx} className="flex items-center gap-1">
                      <input
                        type="text"
                        value={response.text}
                        onChange={(e) => updateResponse(node.id, idx, { text: e.target.value })}
                        className="flex-1 bg-white/20 text-white text-xs px-2 py-1 rounded"
                        onClick={(e) => e.stopPropagation()}
                      />
                      <select
                        value={response.nextId || ''}
                        onChange={(e) => updateResponse(node.id, idx, { nextId: e.target.value || undefined })}
                        className="bg-white/20 text-white text-xs px-2 py-1 rounded"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <option value="">无跳转</option>
                        {dialogues.filter(n => n.id !== node.id).map(n => (
                          <option key={n.id} value={n.id}>{n.text.substring(0, 10)}...</option>
                        ))}
                      </select>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          deleteResponse(node.id, idx)
                        }}
                        className="text-white/60 hover:text-white p-1"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      addResponse(node.id)
                    }}
                    className="w-full text-xs text-white/60 hover:text-white py-1"
                  >
                    + 添加选项
                  </button>
                </div>
              )}
            </div>
          ))}

          {dialogues.length === 0 && (
            <div className="absolute inset-0 flex items-center justify-center text-gray-500">
              <div className="text-center">
                <MessageSquare className="w-12 h-12 mx-auto mb-2 text-gray-300" />
                <p>点击上方按钮添加对话节点</p>
                <p className="text-sm text-gray-400 mt-1">第一个节点将自动设为开始节点</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

const SceneEditor = ({ elements, onUpdate }: { elements: SceneElement[], onUpdate: (elements: SceneElement[]) => void }) => {
  const addElement = (type: SceneElement['type']) => {
    const names = {
      target: '靶标',
      enemy: '敌人',
      obstacle: '障碍',
      powerup: '增益道具',
      collectible: '收集品'
    }
    const newElement: SceneElement = {
      id: `element-${Date.now()}`,
      type,
      position: { x: 0, y: 1, z: -10 },
      points: type === 'target' ? 10 : type === 'enemy' ? 25 : type === 'collectible' ? 5 : 0,
      name: names[type]
    }
    onUpdate([...elements, newElement])
  }

  const deleteElement = (id: string) => {
    onUpdate(elements.filter(e => e.id !== id))
  }

  const updateElement = (id: string, updates: Partial<SceneElement>) => {
    onUpdate(elements.map(e => e.id === id ? { ...e, ...updates } : e))
  }

  const elementColors = {
    target: 'bg-red-100 text-red-700 border-red-200',
    enemy: 'bg-purple-100 text-purple-700 border-purple-200',
    obstacle: 'bg-gray-100 text-gray-700 border-gray-200',
    powerup: 'bg-yellow-100 text-yellow-700 border-yellow-200',
    collectible: 'bg-green-100 text-green-700 border-green-200'
  }

  const elementIcons = {
    target: Target,
    enemy: Bot,
    obstacle: Sparkles,
    powerup: Zap,
    collectible: Check
  }

  return (
    <div className="bg-white rounded-xl p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
          <Sparkles className="w-5 h-5" />
          3D 场景元素
        </h2>
      </div>

      <div className="flex flex-wrap gap-2 mb-4">
        {Object.entries({ target: '靶标', enemy: '敌人', obstacle: '障碍', powerup: '道具', collectible: '收集品' }).map(([type, label]) => (
          <button
            key={type}
            onClick={() => addElement(type as SceneElement['type'])}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg hover:opacity-80 ${elementColors[type as SceneElement['type']]}`}
          >
            {elementIcons[type as SceneElement['type']] && (
              React.createElement(elementIcons[type as SceneElement['type']], { className: 'w-4 h-4' })
            )}
            {label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
        {elements.map((element) => {
          const Icon = elementIcons[element.type]
          return (
            <div key={element.id} className={`p-4 rounded-lg border-2 ${elementColors[element.type]}`}>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  {Icon && <Icon className="w-4 h-4" />}
                  <span className="font-medium">{element.name || element.type}</span>
                </div>
                <button
                  onClick={() => deleteElement(element.id)}
                  className="p-1 hover:bg-white/50 rounded"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
              <div className="space-y-2 text-sm">
                <div className="grid grid-cols-3 gap-1">
                  <div>
                    <label className="text-xs opacity-70">X</label>
                    <input
                      type="number"
                      value={element.position.x}
                      onChange={(e) => updateElement(element.id, { position: { ...element.position, x: parseFloat(e.target.value) } })}
                      className="w-full bg-white/50 rounded px-1 py-0.5 text-center"
                      step="0.5"
                    />
                  </div>
                  <div>
                    <label className="text-xs opacity-70">Y</label>
                    <input
                      type="number"
                      value={element.position.y}
                      onChange={(e) => updateElement(element.id, { position: { ...element.position, y: parseFloat(e.target.value) } })}
                      className="w-full bg-white/50 rounded px-1 py-0.5 text-center"
                      step="0.5"
                    />
                  </div>
                  <div>
                    <label className="text-xs opacity-70">Z</label>
                    <input
                      type="number"
                      value={element.position.z}
                      onChange={(e) => updateElement(element.id, { position: { ...element.position, z: parseFloat(e.target.value) } })}
                      className="w-full bg-white/50 rounded px-1 py-0.5 text-center"
                      step="0.5"
                    />
                  </div>
                </div>
                {element.points !== undefined && (
                  <div>
                    <label className="text-xs opacity-70">分数</label>
                    <input
                      type="number"
                      value={element.points}
                      onChange={(e) => updateElement(element.id, { points: parseInt(e.target.value) })}
                      className="w-full bg-white/50 rounded px-1 py-0.5"
                      min="0"
                    />
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {elements.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          <Target className="w-12 h-12 mx-auto mb-2 text-gray-300" />
          <p>点击上方按钮添加场景元素</p>
        </div>
      )}
    </div>
  )
}

const RealTimePreview = ({ level }: { level: Record<string, unknown> }) => {
  const tasks = (level.tasks as Record<string, unknown>[]) || []
  const dialogues = (level.dialogue_nodes as DialogueNode[]) || []

  return (
    <div className="bg-gradient-to-br from-blue-900 via-purple-900 to-indigo-900 rounded-xl overflow-hidden">
      <div className="p-4 border-b border-white/10">
        <div className="flex items-center justify-between">
          <h3 className="text-white font-medium flex items-center gap-2">
            <Eye className="w-4 h-4" />
            实时预览
          </h3>
          <span className="text-xs text-white/50">{tasks.length} 个任务</span>
        </div>
      </div>
      <div className="p-4 min-h-[300px]">
        <div className="space-y-3">
          {tasks.slice(0, 3).map((task, idx) => (
            <div key={idx} className="bg-white/10 rounded-lg p-3 backdrop-blur-sm">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-white/60 text-xs">#{idx + 1}</span>
                <span className="px-2 py-0.5 bg-white/20 rounded text-xs text-white">
                  {task.type === 'single_choice' ? '单选' : task.type === 'multiple_choice' ? '多选' : task.type === 'true_false' ? '判断' : task.type === 'fill_blank' ? '填空' : task.type === 'shooting' ? '射击' : task.type}
                </span>
                <span className="text-white/40 text-xs">
                  {task.points}分 · 难度{task.difficulty}
                </span>
              </div>
              <p className="text-white text-sm line-clamp-2">{task.content}</p>
              {task.options && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {((task.options as string[]) || []).slice(0, 4).map((opt, i) => (
                    <span key={i} className="px-2 py-0.5 bg-white/10 rounded text-xs text-white/80">
                      {String.fromCharCode(65 + i)}. {opt.substring(0, 10)}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
          {tasks.length > 3 && (
            <div className="text-center py-2 text-white/40 text-sm">
              还有 {tasks.length - 3} 个任务...
            </div>
          )}
          {tasks.length === 0 && (
            <div className="text-center py-8 text-white/30">
              <p>暂无任务</p>
            </div>
          )}
        </div>

        {dialogues.length > 0 && (
          <div className="mt-4 pt-4 border-t border-white/10">
            <div className="text-white/60 text-xs mb-2">对话节点: {dialogues.length}</div>
            <div className="flex flex-wrap gap-1">
              {dialogues.map((node, idx) => (
                <span key={idx} className={`px-2 py-1 rounded text-xs ${
                  node.type === 'start' ? 'bg-green-500/30 text-green-300' :
                  node.type === 'end' ? 'bg-gray-500/30 text-gray-300' :
                  'bg-blue-500/30 text-blue-300'
                }`}>
                  {node.type === 'start' ? '开始' : node.type === 'end' ? '结束' : `节点${idx}`}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

const TabButton = ({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) => (
  <button
    onClick={onClick}
    className={`px-4 py-2 rounded-lg font-medium transition-colors ${
      active
        ? "bg-blue-600 text-white shadow-md"
        : "bg-gray-100 text-gray-700 hover:bg-gray-200"
    }`}
  >
    {children}
  </button>
)

export default function LevelEditor({ levelId, initialData, onSave, onPreview }: LevelEditorProps) {
  const [level, setLevel] = useState<Record<string, unknown>>(() => {
    if (initialData) return initialData as Record<string, unknown>
    return createLevelTemplate(levelId || 'new-level', '新关卡')
  })
  const [saving, setSaving] = useState(false)
  const [errors, setErrors] = useState<string[]>([])
  const [activeTab, setActiveTab] = useState<'tasks' | 'dialogue' | 'scene' | 'settings'>('tasks')
  const [showPreview, setShowPreview] = useState(true)

  const handleAddTask = useCallback(() => {
    const tasks = [...((level.tasks as Record<string, unknown>[]) || [])]
    tasks.push(createTaskTemplate(`task-${Date.now()}`, 'single_choice', '新题目'))
    setLevel({ ...level, tasks })
  }, [level])

  const handleUpdateTask = useCallback((index: number, task: Record<string, unknown>) => {
    const tasks = [...((level.tasks as Record<string, unknown>[]) || [])]
    tasks[index] = task
    setLevel({ ...level, tasks })
  }, [level])

  const handleDeleteTask = useCallback((index: number) => {
    const tasks = [...((level.tasks as Record<string, unknown>[]) || [])]
    tasks.splice(index, 1)
    setLevel({ ...level, tasks })
  }, [level])

  const handleMoveTask = useCallback((fromIndex: number, toIndex: number) => {
    const tasks = [...((level.tasks as Record<string, unknown>[]) || [])]
    const [removed] = tasks.splice(fromIndex, 1)
    tasks.splice(toIndex, 0, removed)
    setLevel({ ...level, tasks })
  }, [level])

  const handleUpdateDialogueNodes = (nodes: DialogueNode[]) => {
    setLevel({ ...level, dialogue_nodes: nodes })
  }

  const handleUpdateSceneElements = (elements: SceneElement[]) => {
    setLevel({ ...level, scene_elements: elements })
  }

  const handleSave = async () => {
    setSaving(true)
    setErrors([])

    const validation = validateLevelDSL(level)
    if (!validation.valid) {
      setErrors(validation.errors)
      setSaving(false)
      return
    }

    try {
      await onSave(level)
    } catch {
      setErrors(['保存失败，请重试'])
    } finally {
      setSaving(false)
    }
  }

  const handleReset = () => {
    if (confirm('确定要重置关卡吗？所有修改将丢失。')) {
      setLevel(createLevelTemplate(levelId || 'new-level', '新关卡'))
      setErrors([])
    }
  }

  const tasks = (level.tasks as Record<string, unknown>[]) || []

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-white border-b border-gray-200 px-6 py-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-bold text-gray-800">关卡编辑器</h1>
            <input
              type="text"
              value={level.name as string}
              onChange={(e) => setLevel({ ...level, name: e.target.value })}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-lg w-64"
              placeholder="关卡名称"
            />
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleReset}
              className="flex items-center gap-2 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
            >
              <RotateCcw className="w-4 h-4" />
              重置
            </button>
            <button
              onClick={() => onPreview(level)}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 shadow-md"
            >
              <Play className="w-4 h-4" />
              预览游戏
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 shadow-md disabled:opacity-50"
            >
              <Save className="w-4 h-4" />
              {saving ? '保存中...' : '保存关卡'}
            </button>
          </div>
        </div>
      </header>

      <main className="p-6">
        {errors.length > 0 && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <h3 className="font-medium text-red-800 mb-2">验证错误：</h3>
            <ul className="list-disc list-inside text-red-600 text-sm">
              {errors.map((err, idx) => (
                <li key={idx}>{err}</li>
              ))}
            </ul>
          </div>
        )}

        <div className="flex gap-2 mb-6">
          <TabButton active={activeTab === 'tasks'} onClick={() => setActiveTab('tasks')}>
            任务列表
          </TabButton>
          <TabButton active={activeTab === 'dialogue'} onClick={() => setActiveTab('dialogue')}>
            对话树
          </TabButton>
          <TabButton active={activeTab === 'scene'} onClick={() => setActiveTab('scene')}>
            3D 场景
          </TabButton>
          <TabButton active={activeTab === 'settings'} onClick={() => setActiveTab('settings')}>
            关卡设置
          </TabButton>
        </div>

        <div className="grid grid-cols-12 gap-6">
          <div className="col-span-9">
            {activeTab === 'tasks' && (
              <div className="bg-white rounded-xl p-6 shadow-sm">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold text-gray-800">题目任务</h2>
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-gray-500">{tasks.length} 个任务</span>
                    <button
                      onClick={handleAddTask}
                      className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                    >
                      <Plus className="w-4 h-4" />
                      添加任务
                    </button>
                  </div>
                </div>

                <div className="space-y-3">
                  {tasks.map((task, index) => (
                    <TaskEditor
                      key={task.id as string || index}
                      task={task}
                      index={index}
                      onUpdate={handleUpdateTask}
                      onDelete={handleDeleteTask}
                      onMoveUp={() => handleMoveTask(index, index - 1)}
                      onMoveDown={() => handleMoveTask(index, index + 1)}
                      totalTasks={tasks.length}
                    />
                  ))}
                </div>

                {tasks.length === 0 && (
                  <div className="text-center py-12 text-gray-500">
                    <Wand2 className="w-12 h-12 mx-auto mb-2 text-gray-300" />
                    <p>暂无任务</p>
                    <button
                      onClick={handleAddTask}
                      className="mt-2 text-blue-600 hover:text-blue-700"
                    >
                      添加第一个任务
                    </button>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'dialogue' && (
              <NPCDialogueTreeEditor
                dialogues={(level.dialogue_nodes as DialogueNode[]) || []}
                onUpdate={handleUpdateDialogueNodes}
              />
            )}

            {activeTab === 'scene' && (
              <SceneEditor
                elements={(level.scene_elements as SceneElement[]) || []}
                onUpdate={handleUpdateSceneElements}
              />
            )}

            {activeTab === 'settings' && (
              <div className="bg-white rounded-xl p-6 shadow-sm">
                <h2 className="text-lg font-semibold text-gray-800 mb-4">关卡设置</h2>
                <div className="grid grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">关卡ID</label>
                    <input
                      type="text"
                      value={level.id as string}
                      onChange={(e) => setLevel({ ...level, id: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">关卡类型</label>
                    <select
                      value={level.type as string || 'quiz'}
                      onChange={(e) => setLevel({ ...level, type: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="quiz">答题模式</option>
                      <option value="shooting">射击模式</option>
                      <option value="puzzle">解谜模式</option>
                      <option value="adventure">冒险模式</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
                    <textarea
                      value={(level.description as string) || ''}
                      onChange={(e) => setLevel({ ...level, description: e.target.value })}
                      rows={3}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
                    />
                  </div>

                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">难度 (1-5)</label>
                      <input
                        type="number"
                        min={1}
                        max={5}
                        value={level.difficulty as number || 1}
                        onChange={(e) => setLevel({ ...level, difficulty: parseInt(e.target.value) })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">最高分</label>
                      <input
                        type="number"
                        value={level.max_score as number || 100}
                        onChange={(e) => setLevel({ ...level, max_score: parseInt(e.target.value) })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        min="1"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">时间限制（秒）</label>
                    <input
                      type="number"
                      value={level.time_limit as number || 0}
                      onChange={(e) => setLevel({ ...level, time_limit: parseInt(e.target.value) })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      min="0"
                    />
                    <p className="text-xs text-gray-500 mt-1">0 表示无时间限制</p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">奖励设置</label>
                    <div className="grid grid-cols-3 gap-2">
                      <div>
                        <label className="text-xs text-gray-500">经验</label>
                        <input
                          type="number"
                          value={(level.rewards as Record<string, unknown>)?.experience as number || 50}
                          onChange={(e) => setLevel({
                            ...level,
                            rewards: { ...(level.rewards as Record<string, unknown>), experience: parseInt(e.target.value) }
                          })}
                          className="w-full px-2 py-1 border border-gray-300 rounded focus:ring-1 focus:ring-blue-500"
                          min="0"
                        />
                      </div>
                      <div>
                        <label className="text-xs text-gray-500">金币</label>
                        <input
                          type="number"
                          value={(level.rewards as Record<string, unknown>)?.coins as number || 100}
                          onChange={(e) => setLevel({
                            ...level,
                            rewards: { ...(level.rewards as Record<string, unknown>), coins: parseInt(e.target.value) }
                          })}
                          className="w-full px-2 py-1 border border-gray-300 rounded focus:ring-1 focus:ring-blue-500"
                          min="0"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="col-span-3 space-y-4">
            <div className="bg-white rounded-xl p-4 shadow-sm">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-medium text-gray-800">AI 辅助生成</h3>
                <button
                  onClick={() => alert('AI 生成功能需要配置 Claude API Key')}
                  className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700"
                >
                  <Sparkles className="w-3 h-3" />
                  配置
                </button>
              </div>
              <button
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-lg hover:from-purple-700 hover:to-blue-700 mb-3"
                onClick={() => alert('AI 生成功能需要配置 Claude API Key')}
              >
                <Sparkles className="w-4 h-4" />
                一键 AI 生成
              </button>
              <div className="grid grid-cols-2 gap-2">
                <button
                  className="flex items-center justify-center gap-1 px-3 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-sm"
                  onClick={() => alert('AI 生成功能需要配置 Claude API Key')}
                >
                  <Wand2 className="w-3 h-3" />
                  生成题目
                </button>
                <button
                  className="flex items-center justify-center gap-1 px-3 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-sm"
                  onClick={() => alert('AI 生成功能需要配置 Claude API Key')}
                >
                  <MessageSquare className="w-3 h-3" />
                  生成对话
                </button>
              </div>
            </div>

            {showPreview && (
              <RealTimePreview level={level} />
            )}

            <div className="bg-white rounded-xl p-4 shadow-sm">
              <h3 className="font-medium text-gray-800 mb-3">关卡统计</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500">任务数量</span>
                  <span className="font-medium">{tasks.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">总分值</span>
                  <span className="font-medium">{tasks.reduce((sum, t) => sum + (t.points as number || 10), 0)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">平均难度</span>
                  <span className="font-medium">{tasks.length > 0 ? (tasks.reduce((sum, t) => sum + (t.difficulty as number || 1), 0) / tasks.length).toFixed(1) : 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">对话节点</span>
                  <span className="font-medium">{((level.dialogue_nodes as DialogueNode[]) || []).length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">场景元素</span>
                  <span className="font-medium">{((level.scene_elements as SceneElement[]) || []).length}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
