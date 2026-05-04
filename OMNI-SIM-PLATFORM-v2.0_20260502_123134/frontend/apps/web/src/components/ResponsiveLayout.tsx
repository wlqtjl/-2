import { useState, useEffect } from 'react'
import { Menu, X, Smartphone, Tablet, Monitor } from 'lucide-react'

// 断点定义
export const breakpoints = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280
}

// 设备类型
export type DeviceType = 'mobile' | 'tablet' | 'desktop'

export function useDeviceType(): DeviceType {
  const [deviceType, setDeviceType] = useState<DeviceType>('desktop')

  useEffect(() => {
    const updateDeviceType = () => {
      const width = window.innerWidth
      if (width < breakpoints.md) {
        setDeviceType('mobile')
      } else if (width < breakpoints.lg) {
        setDeviceType('tablet')
      } else {
        setDeviceType('desktop')
      }
    }

    updateDeviceType()
    window.addEventListener('resize', updateDeviceType)
    return () => window.removeEventListener('resize', updateDeviceType)
  }, [])

  return deviceType
}

export function useIsMobile(): boolean {
  return useDeviceType() === 'mobile'
}

export function useIsTablet(): boolean {
  return useDeviceType() === 'tablet'
}

export function useIsDesktop(): boolean {
  return useDeviceType() === 'desktop'
}

export function useIsSmallScreen(): boolean {
  return useDeviceType() === 'mobile' || useDeviceType() === 'tablet'
}

// 响应式容器组件
export function ResponsiveContainer({ children }: { children: React.ReactNode }) {
  return (
    <div className="w-full mx-auto px-4 sm:px-6 md:px-8">
      <div className="max-w-7xl mx-auto">
        {children}
      </div>
    </div>
  )
}

// 响应式网格组件
export function ResponsiveGrid({ 
  children, 
  columns = '1',
  gap = '4'
}: { 
  children: React.ReactNode
  columns?: string
  gap?: string
}) {
  const columnClasses: Record<string, string> = {
    '1': 'grid-cols-1',
    '2': 'grid-cols-1 sm:grid-cols-2',
    '3': 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3',
    '4': 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-4',
    'auto': 'grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6'
  }

  const gapClasses: Record<string, string> = {
    '1': 'gap-1',
    '2': 'gap-2',
    '3': 'gap-3',
    '4': 'gap-4',
    '6': 'gap-6',
    '8': 'gap-8'
  }

  return (
    <div className={`grid ${columnClasses[columns]} ${gapClasses[gap]}`}>
      {children}
    </div>
  )
}

// 响应式卡片组件
export function ResponsiveCard({ 
  children, 
  className = '',
  onClick
}: { 
  children: React.ReactNode
  className?: string
  onClick?: () => void
}) {
  return (
    <div 
      className={`bg-white rounded-xl shadow-sm p-4 sm:p-6 ${className} transition-all duration-300 hover:shadow-md ${
        onClick ? 'cursor-pointer hover:scale-[1.02]' : ''
      }`}
      onClick={onClick}
    >
      {children}
    </div>
  )
}

// 移动端导航组件
export function MobileNav({ 
  isOpen, 
  onToggle, 
  children 
}: { 
  isOpen: boolean
  onToggle: () => void
  children: React.ReactNode
}) {
  return (
    <>
      <button
        onClick={onToggle}
        className="md:hidden p-2 rounded-lg hover:bg-gray-100"
        aria-label="Toggle menu"
      >
        {isOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
      </button>
      
      <div 
        className={`md:hidden fixed inset-0 z-50 transition-all duration-300 ${
          isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
        }`}
      >
        {/* 遮罩层 */}
        <div 
          className="absolute inset-0 bg-black/50"
          onClick={onToggle}
        />
        
        {/* 导航菜单 */}
        <div className="absolute left-0 top-0 h-full w-64 bg-white shadow-xl transform transition-transform duration-300">
          <div className="p-4 border-b">
            <div className="flex items-center justify-between">
              <span className="font-bold text-lg">培训平台</span>
              <button onClick={onToggle}>
                <X className="w-6 h-6" />
              </button>
            </div>
          </div>
          <nav className="p-4 space-y-2">
            {children}
          </nav>
        </div>
      </div>
    </>
  )
}

// 设备指示器（开发用）
export function DeviceIndicator() {
  const deviceType = useDeviceType()

  const deviceConfig = {
    mobile: { icon: Smartphone, color: 'bg-green-500', label: 'Mobile' },
    tablet: { icon: Tablet, color: 'bg-blue-500', label: 'Tablet' },
    desktop: { icon: Monitor, color: 'bg-purple-500', label: 'Desktop' }
  }

  const config = deviceConfig[deviceType]
  const Icon = config.icon

  return (
    <div className="fixed bottom-4 right-4 z-50">
      <div className={`flex items-center gap-2 px-3 py-2 ${config.color} text-white rounded-full text-sm shadow-lg`}>
        <Icon className="w-4 h-4" />
        <span>{config.label}</span>
      </div>
    </div>
  )
}

// 响应式按钮组件
export function ResponsiveButton({ 
  children, 
  variant = 'primary',
  size = 'default',
  onClick,
  className = ''
}: { 
  children: React.ReactNode
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost'
  size?: 'sm' | 'default' | 'lg'
  onClick?: () => void
  className?: string
}) {
  const variants: Record<string, string> = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700',
    secondary: 'bg-gray-100 text-gray-700 hover:bg-gray-200',
    outline: 'border border-blue-600 text-blue-600 hover:bg-blue-50',
    ghost: 'text-gray-600 hover:bg-gray-100'
  }

  const sizes: Record<string, string> = {
    sm: 'px-3 py-1.5 text-sm',
    default: 'px-4 py-2 text-sm',
    lg: 'px-6 py-3 text-base'
  }

  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors ${variants[variant]} ${sizes[size]} ${className}`}
    >
      {children}
    </button>
  )
}

// 响应式文本组件
export function ResponsiveText({ 
  children, 
  variant = 'body'
}: { 
  children: React.ReactNode
  variant?: 'heading1' | 'heading2' | 'heading3' | 'heading4' | 'body' | 'caption'
}) {
  const variants: Record<string, string> = {
    heading1: 'text-2xl sm:text-3xl md:text-4xl font-bold',
    heading2: 'text-xl sm:text-2xl md:text-3xl font-semibold',
    heading3: 'text-lg sm:text-xl font-semibold',
    heading4: 'text-base sm:text-lg font-medium',
    body: 'text-sm sm:text-base',
    caption: 'text-xs sm:text-sm text-gray-500'
  }

  return (
    <span className={`${variants[variant]}`}>
      {children}
    </span>
  )
}

// 响应式图片组件
export function ResponsiveImage({ 
  src, 
  alt,
  className = ''
}: { 
  src: string
  alt: string
  className?: string
}) {
  return (
    <img
      src={src}
      alt={alt}
      className={`max-w-full h-auto rounded-lg ${className}`}
      loading="lazy"
    />
  )
}

// 响应式表单组件
export function ResponsiveInput({ 
  type = 'text',
  placeholder = '',
  value,
  onChange,
  className = ''
}: { 
  type?: string
  placeholder?: string
  value?: string
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void
  className?: string
}) {
  return (
    <input
      type={type}
      placeholder={placeholder}
      value={value}
      onChange={onChange}
      className={`w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors ${className}`}
    />
  )
}

// 响应式选择组件
export function ResponsiveSelect({ 
  options,
  value,
  onChange,
  className = ''
}: { 
  options: { value: string; label: string }[]
  value?: string
  onChange?: (e: React.ChangeEvent<HTMLSelectElement>) => void
  className?: string
}) {
  return (
    <select
      value={value}
      onChange={onChange}
      className={`w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors bg-white ${className}`}
    >
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  )
}