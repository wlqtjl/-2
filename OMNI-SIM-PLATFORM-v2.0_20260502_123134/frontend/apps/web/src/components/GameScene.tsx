import { useRef, useMemo, useState, useEffect, useCallback } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { OrbitControls, Box, Text, Float, Stars, Sky, Sphere, Cylinder, Sparkles, Ring, Torus, Cone, Capsule, Line, Html } from '@react-three/drei'
import * as THREE from 'three'

interface GameSceneProps {
  questionIndex: number
  isCorrect: boolean
  showFeedback: boolean
  levelName?: string
  onTargetHit?: (targetId: number, points: number) => void
  enableVR?: boolean
  score?: number
  health?: number
  onScoreChange?: (score: number) => void
  onHealthChange?: (health: number) => void
}

type GameElementType = 'target' | 'enemy' | 'powerup' | 'obstacle' | 'achievement' | 'boss' | 'bullet' | 'minion' | 'collectible' | 'portal'

interface GameElement {
  id: number
  type: GameElementType
  position: [number, number, number]
  color: string
  emoji?: string
  points?: number
  scale?: number
  health?: number
}

interface BulletData {
  id: number
  position: THREE.Vector3
  velocity: THREE.Vector3
  damage: number
}

interface EnemyData {
  id: number
  position: THREE.Vector3
  targetPosition: THREE.Vector3
  health: number
  maxHealth: number
  speed: number
  attackCooldown: number
  lastAttackTime: number
}

function PlayerAvatar({ onHealthChange, health }: { onHealthChange?: (health: number) => void; health?: number }) {
  const [bobOffset, setBobOffset] = useState(0)
  const meshRef = useRef<THREE.Group>(null)
  const { camera } = useThree()
  
  useFrame((state, delta) => {
    setBobOffset(Math.sin(state.clock.elapsedTime * 2) * 0.05)
    
    if (meshRef.current && camera) {
      const cameraDirection = new THREE.Vector3()
      camera.getWorldDirection(cameraDirection)
      cameraDirection.y = 0
      cameraDirection.normalize()
      
      const lookAt = new THREE.Vector3()
      lookAt.copy(meshRef.current.position).add(cameraDirection)
      meshRef.current.lookAt(lookAt)
    }
  })

  return (
    <group ref={meshRef} position={[0, bobOffset, 0]}>
      <Sphere args={[0.3, 16, 16]} position={[0, 1.5, 0]}>
        <meshStandardMaterial color="#ffd700" />
      </Sphere>
      <Box args={[0.4, 0.6, 0.2]} position={[0, 1, 0]}>
        <meshStandardMaterial color="#4a90e2" />
      </Box>
      <Box args={[0.15, 0.4, 0.15]} position={[-0.15, 0.6, 0]}>
        <meshStandardMaterial color="#2c3e50" />
      </Box>
      <Box args={[0.15, 0.4, 0.15]} position={[0.15, 0.6, 0]}>
        <meshStandardMaterial color="#2c3e50" />
      </Box>
      
      {(health !== undefined && health < 100) && (
        <group position={[0, 2.2, 0]}>
          <Box args={[0.8, 0.1, 0.1]}>
            <meshStandardMaterial color="#374151" />
          </Box>
          <Box args={[0.76 * (health / 100), 0.08, 0.08]} position={[(-0.38) + 0.38 * (health / 100), 0, 0]}>
            <meshStandardMaterial color={health > 50 ? '#22c55e' : health > 25 ? '#eab308' : '#ef4444'} />
          </Box>
        </group>
      )}
    </group>
  )
}

function Target({ position, color, emoji = '🎯', onClick, points = 10, isHit, onHit }: {
  position: [number, number, number],
  color: string,
  emoji?: string,
  onClick?: () => void,
  points?: number,
  isHit?: boolean,
  onHit?: () => void
}) {
  const [hovered, setHovered] = useState(false)

  if (isHit) return null

  return (
    <Float speed={2} rotationIntensity={0.5} floatIntensity={0.5}>
      <group position={position}>
        <Box args={[1, 1, 0.2]} onClick={onClick} onPointerOver={() => setHovered(true)} onPointerOut={() => setHovered(false)}>
          <meshStandardMaterial
            color={color}
            emissive={hovered ? color : 'black'}
            emissiveIntensity={hovered ? 0.5 : 0}
          />
        </Box>
        <Text position={[0, 0, 0.2]} fontSize={0.4} color="white" anchorX="center" anchorY="middle">
          {emoji}
        </Text>
        {hovered && (
          <Text position={[0, 0.8, 0]} fontSize={0.2} color="#ffd700" anchorX="center" anchorY="middle">
            +{points}
          </Text>
        )}
      </group>
    </Float>
  )
}

function Enemy({ position, color, emoji = '👾', onClick, points = 25, health = 100, maxHealth = 100 }: {
  position: [number, number, number],
  color: string,
  emoji?: string,
  onClick?: () => void,
  points?: number,
  health?: number,
  maxHealth?: number
}) {
  const [hovered, setHovered] = useState(false)
  const meshRef = useRef<THREE.Mesh>(null)
  const healthPercent = (health / maxHealth) * 100

  useFrame((state, delta) => {
    if (meshRef.current) {
      meshRef.current.position.y += Math.sin(state.clock.elapsedTime * 2 + position[0]) * 0.01
      meshRef.current.rotation.z += delta * 0.5
    }
  })

  return (
    <Float speed={3} rotationIntensity={1} floatIntensity={0.8}>
      <group position={position}>
        <Sphere ref={meshRef} args={[0.6, 16, 16]} onClick={onClick} onPointerOver={() => setHovered(true)} onPointerOut={() => setHovered(false)}>
          <meshStandardMaterial
            color={color}
            emissive={hovered ? color : '#330000'}
            emissiveIntensity={hovered ? 0.8 : 0.2}
          />
        </Sphere>
        <Ring args={[0.4, 0.6, 8]} position={[0, 0, 0.6]}>
          <meshStandardMaterial color={color} opacity={0.5} transparent />
        </Ring>
        <Text position={[0, 0, 0.7]} fontSize={0.4} color="white" anchorX="center" anchorY="middle">
          {emoji}
        </Text>
        
        <group position={[0, 0.9, 0]}>
          <Box args={[0.6, 0.08, 0.05]}>
            <meshStandardMaterial color="#374151" />
          </Box>
          <Box args={[0.56 * (healthPercent / 100), 0.06, 0.04]} position={[(-0.28) + 0.28 * (healthPercent / 100), 0, 0]}>
            <meshStandardMaterial color="#ef4444" />
          </Box>
        </group>
        
        {hovered && (
          <Text position={[0, 1.2, 0]} fontSize={0.2} color="#ff4444" anchorX="center" anchorY="middle">
            +{points}
          </Text>
        )}
      </group>
    </Float>
  )
}

function Boss({ position, color, emoji = '🐉', onClick, points = 100, health = 500, maxHealth = 500 }: {
  position: [number, number, number],
  color: string,
  emoji?: string,
  onClick?: () => void,
  points?: number,
  health?: number,
  maxHealth?: number
}) {
  const [hovered, setHovered] = useState(false)
  const meshRef = useRef<THREE.Group>(null)
  const healthPercent = (health / maxHealth) * 100

  useFrame((state, delta) => {
    if (meshRef.current) {
      meshRef.current.rotation.y += delta * 0.3
    }
  })

  return (
    <Float speed={1} rotationIntensity={0.3} floatIntensity={1}>
      <group ref={meshRef} position={position}>
        <Torus args={[1.2, 0.2, 8, 16]}>
          <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.3} />
        </Torus>
        <Torus args={[1.5, 0.15, 8, 16]} position={[0, 0, -0.1]}>
          <meshStandardMaterial color="#ff6b6b" emissive="#ff6b6b" emissiveIntensity={0.2} />
        </Torus>
        <Sphere args={[0.8, 16, 16]} onClick={onClick} onPointerOver={() => setHovered(true)} onPointerOut={() => setHovered(false)}>
          <meshStandardMaterial color={color} emissive={hovered ? color : '#220000'} emissiveIntensity={hovered ? 0.6 : 0.1} />
        </Sphere>
        <Text position={[0, 0, 0.9]} fontSize={0.5} color="white" anchorX="center" anchorY="middle">
          {emoji}
        </Text>
        
        <group position={[0, 1.5, 0]}>
          <Box args={[1.2, 0.12, 0.05]}>
            <meshStandardMaterial color="#374151" />
          </Box>
          <Box args={[1.16 * (healthPercent / 100), 0.1, 0.04]} position={[(-0.58) + 0.58 * (healthPercent / 100), 0, 0]}>
            <meshStandardMaterial color="#ef4444" />
          </Box>
        </group>
        
        {hovered && (
          <Text position={[0, 2, 0]} fontSize={0.25} color="#ffd700" anchorX="center" anchorY="middle">
            BOSS! +{points}
          </Text>
        )}
      </group>
    </Float>
  )
}

function Minion({ position, color, emoji = '👻', onClick, points = 15, health = 50, maxHealth = 50 }: {
  position: [number, number, number],
  color: string,
  emoji?: string,
  onClick?: () => void,
  points?: number,
  health?: number,
  maxHealth?: number
}) {
  const [hovered, setHovered] = useState(false)
  const meshRef = useRef<THREE.Group>(null)
  const healthPercent = (health / maxHealth) * 100

  useFrame((state, delta) => {
    if (meshRef.current) {
      meshRef.current.position.y += Math.sin(state.clock.elapsedTime * 3 + position[0]) * 0.015
      meshRef.current.rotation.y += delta * 0.8
    }
  })

  return (
    <Float speed={5} rotationIntensity={1.5} floatIntensity={1.2}>
      <group ref={meshRef} position={position}>
        <Capsule args={[0.2, 0.6, 8, 16]} onClick={onClick} onPointerOver={() => setHovered(true)} onPointerOut={() => setHovered(false)}>
          <meshStandardMaterial color={color} emissive={hovered ? color : '#1a1a2e'} emissiveIntensity={hovered ? 0.7 : 0.1} />
        </Capsule>
        <Sphere args={[0.25, 12, 12]} position={[0, 0.4, 0]}>
          <meshStandardMaterial color={color} />
        </Sphere>
        <Text position={[0, 0, 0.45]} fontSize={0.25} color="white" anchorX="center" anchorY="middle">
          {emoji}
        </Text>
        
        {healthPercent < 100 && (
          <group position={[0, 0.75, 0]}>
            <Box args={[0.4, 0.06, 0.03]}>
              <meshStandardMaterial color="#374151" />
            </Box>
            <Box args={[0.38 * (healthPercent / 100), 0.04, 0.02]} position={[(-0.19) + 0.19 * (healthPercent / 100), 0, 0]}>
              <meshStandardMaterial color="#ef4444" />
            </Box>
          </group>
        )}
        
        {hovered && (
          <Text position={[0, 1, 0]} fontSize={0.2} color={color} anchorX="center" anchorY="middle">
            +{points}
          </Text>
        )}
      </group>
    </Float>
  )
}

function Obstacle({ position, size = [1.5, 1.5, 1.5] as [number, number, number], color = '#64748b' }: {
  position: [number, number, number],
  size?: [number, number, number],
  color?: string
}) {
  return (
    <Box args={size} position={position}>
      <meshStandardMaterial color={color} roughness={0.8} />
    </Box>
  )
}

function PowerUp({ position, type = 'star', onClick }: {
  position: [number, number, number],
  type?: 'star' | 'shield' | 'speed' | 'health',
  onClick?: () => void
}) {
  const colors = {
    star: '#ffd700',
    shield: '#4a90e2',
    speed: '#22c55e',
    health: '#ef4444'
  }
  const emojis = {
    star: '⭐',
    shield: '🛡️',
    speed: '⚡',
    health: '❤️'
  }

  return (
    <Float speed={4} rotationIntensity={1} floatIntensity={1}>
      <group position={position}>
        <Sphere args={[0.4, 16, 16]} onClick={onClick}>
          <meshStandardMaterial color={colors[type]} emissive={colors[type]} emissiveIntensity={0.8} />
        </Sphere>
        <Sparkles count={8} scale={1.2} size={0.3} speed={1.5} opacity={0.8} color={colors[type]} />
        <Text position={[0, 0, 0.5]} fontSize={0.3} color="white" anchorX="center" anchorY="middle">
          {emojis[type]}
        </Text>
      </group>
    </Float>
  )
}

function Collectible({ position, type = 'coin', onClick }: {
  position: [number, number, number],
  type?: 'coin' | 'gem' | 'crystal',
  onClick?: () => void
}) {
  const configs = {
    coin: { color: '#fcd34d', emoji: '🪙', geometry: <Torus args={[0.25, 0.1, 8, 16]} /> },
    gem: { color: '#a78bfa', emoji: '💎', geometry: <coneGeometry args={[0.3, 0.4, 8]} /> },
    crystal: { color: '#22d3ee', emoji: '🔮', geometry: <icosahedronGeometry args={[0.25]} /> }
  }

  const config = configs[type]

  return (
    <Float speed={6} rotationIntensity={2} floatIntensity={0.8}>
      <group position={position}>
        <mesh onClick={onClick}>
          {config.geometry}
          <meshStandardMaterial color={config.color} emissive={config.color} emissiveIntensity={0.5} />
        </mesh>
        <Sparkles count={6} scale={0.8} size={0.2} speed={2} opacity={0.9} color={config.color} />
        <Text position={[0, 0, 0.35]} fontSize={0.2} color="white" anchorX="center" anchorY="middle">
          {config.emoji}
        </Text>
      </group>
    </Float>
  )
}

function Portal({ position, color = '#8b5cf6', onClick }: {
  position: [number, number, number],
  color?: string,
  onClick?: () => void
}) {
  const [scale, setScale] = useState(1)
  
  useFrame((state) => {
    setScale(1 + Math.sin(state.clock.elapsedTime * 2) * 0.1)
  })

  return (
    <group position={position} scale={[scale, scale, scale]}>
      <Torus args={[0.8, 0.15, 12, 32]}>
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.6} />
      </Torus>
      <Torus args={[0.6, 0.1, 12, 32]} rotation={[Math.PI / 2, 0, 0]}>
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.4} />
      </Torus>
      <Sparkles count={15} scale={1.2} size={0.25} speed={1.8} opacity={0.8} color={color} />
      <Text position={[0, 0, 0.85]} fontSize={0.25} color="white" anchorX="center" anchorY="middle">
        🌀
      </Text>
    </group>
  )
}

function Explosion({ position, color = '#ff6b6b', scale = 1 }: { position: [number, number, number], color?: string, scale?: number }) {
  const [visible, setVisible] = useState(true)
  
  useEffect(() => {
    const timer = setTimeout(() => setVisible(false), 800)
    return () => clearTimeout(timer)
  }, [])

  if (!visible) return null

  return (
    <group position={position} scale={[scale, scale, scale]}>
      <Sparkles count={20} scale={1.5} size={0.4} speed={3} opacity={1} color={color} />
      <Sphere args={[0.8, 8, 8]} scale={[1.5, 1.5, 1.5]}>
        <meshBasicMaterial color={color} transparent opacity={0.6} />
      </Sphere>
    </group>
  )
}

function AchievementEffect({ text, show, onComplete }: { text: string; show: boolean; onComplete?: () => void }) {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    if (show) {
      setVisible(true)
      const timer = setTimeout(() => {
        setVisible(false)
        onComplete?.()
      }, 3000)
      return () => clearTimeout(timer)
    }
  }, [show, onComplete])

  if (!visible) return null

  return (
    <group position={[0, 4, 0]}>
      <Sparkles count={30} scale={2.5} size={0.4} speed={2} opacity={0.9} color="#ffd700" />
      <Text
        fontSize={0.6}
        color="#ffd700"
        anchorX="center"
        anchorY="middle"
        position={[0, 0.5, 0]}
      >
        {text}
      </Text>
    </group>
  )
}

function FeedbackEffect({ isCorrect, show }: { isCorrect: boolean; show: boolean }) {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    if (show) {
      setVisible(true)
      const timer = setTimeout(() => {
        setVisible(false)
      }, 1500)
      return () => clearTimeout(timer)
    }
  }, [show, isCorrect])

  if (!visible) return null

  const color = isCorrect ? '#22c55e' : '#ef4444'
  const emoji = isCorrect ? '✓' : '✗'

  return (
    <group position={[0, 1, 0]}>
      <Sparkles count={25} scale={2} size={0.35} speed={2.5} opacity={0.8} color={color} />
      <Text position={[0, 0, 0]} fontSize={1} color={color} anchorX="center" anchorY="middle">
        {emoji}
      </Text>
    </group>
  )
}

function LevelTitle({ text, show }: { text: string; show: boolean }) {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    if (show) {
      setVisible(true)
      const timer = setTimeout(() => setVisible(false), 2000)
      return () => clearTimeout(timer)
    }
  }, [show])

  if (!visible) return null

  return (
    <Text
      position={[0, 4, -5]}
      fontSize={0.8}
      color="#f8fafc"
      anchorX="center"
      anchorY="middle"
    >
      {text}
    </Text>
  )
}

function Bullet({ position, velocity, onUpdate, onDestroy }: {
  position: THREE.Vector3,
  velocity: THREE.Vector3,
  onUpdate: (position: THREE.Vector3) => void,
  onDestroy: () => void
}) {
  const meshRef = useRef<THREE.Mesh>(null)
  const bulletPosition = useRef(position.clone())

  useFrame((state, delta) => {
    if (meshRef.current) {
      bulletPosition.current.add(velocity.clone().multiplyScalar(delta))
      meshRef.current.position.copy(bulletPosition.current)
      onUpdate(bulletPosition.current)

      if (bulletPosition.current.z < -30 || bulletPosition.current.z > 10 || 
          bulletPosition.current.x < -20 || bulletPosition.current.x > 20 ||
          bulletPosition.current.y < -5) {
        onDestroy()
      }
    }
  })

  return (
    <mesh ref={meshRef}>
      <sphereGeometry args={[0.1, 8, 8]} />
      <meshStandardMaterial color="#fbbf24" emissive="#fbbf24" emissiveIntensity={0.8} />
    </mesh>
  )
}

function ShootingRange({ 
  onTargetHit, 
  onScoreChange, 
  onHealthChange,
  health = 100
}: { 
  onTargetHit?: (targetId: number, points: number) => void
  onScoreChange?: (score: number) => void
  onHealthChange?: (health: number) => void
  health?: number
}) {
  const bulletsRef = useRef<BulletData[]>([])
  const enemiesRef = useRef<EnemyData[]>([])
  const [bullets, setBullets] = useState<BulletData[]>([])
  const [explosions, setExplosions] = useState<Array<{id: number; position: [number, number, number]; color: string}>>([])
  const [hitTargets, setHitTargets] = useState<Set<number>>(new Set())
  const bulletIdCounter = useRef(0)
  const explosionIdCounter = useRef(0)
  const { camera } = useThree()

  const targets: GameElement[] = useMemo(() => [
    { id: 1, type: 'target', position: [-6, 1, -10], color: '#ef4444', emoji: '🎯', points: 10 },
    { id: 2, type: 'target', position: [0, 2, -12], color: '#f97316', emoji: '🎯', points: 10 },
    { id: 3, type: 'target', position: [6, 1, -10], color: '#eab308', emoji: '🎯', points: 10 },
    { id: 4, type: 'target', position: [-3, 1.5, -15], color: '#22c55e', emoji: '🎯', points: 15 },
    { id: 5, type: 'target', position: [3, 1.5, -15], color: '#06b6d4', emoji: '🎯', points: 15 },
    { id: 6, type: 'target', position: [0, 0.5, -18], color: '#a855f7', emoji: '🎯', points: 20 },
    { id: 7, type: 'enemy', position: [-8, 2, -12], color: '#dc2626', emoji: '👾', points: 25, health: 100 },
    { id: 8, type: 'enemy', position: [8, 2, -12], color: '#dc2626', emoji: '👾', points: 25, health: 100 },
    { id: 9, type: 'boss', position: [0, 2, -20], color: '#7c3aed', emoji: '🐉', points: 100, health: 500 },
    { id: 10, type: 'minion', position: [-10, 1.5, -14], color: '#f472b6', emoji: '👻', points: 15, health: 50 },
    { id: 11, type: 'minion', position: [10, 1.5, -14], color: '#f472b6', emoji: '👻', points: 15, health: 50 },
    { id: 12, type: 'minion', position: [-7, 2.5, -16], color: '#34d399', emoji: '🎃', points: 18, health: 60 },
    { id: 13, type: 'minion', position: [7, 2.5, -16], color: '#34d399', emoji: '🎃', points: 18, health: 60 },
  ], [])

  const obstacles: GameElement[] = useMemo(() => [
    { id: 1, type: 'obstacle', position: [-4, 0.5, -8], color: '#64748b' },
    { id: 2, type: 'obstacle', position: [4, 0.5, -8], color: '#64748b' },
    { id: 3, type: 'obstacle', position: [0, 1, -6], color: '#64748b' },
  ], [])

  const powerups: GameElement[] = useMemo(() => [
    { id: 1, type: 'powerup', position: [-5, 2, -6], color: '#ffd700' },
    { id: 2, type: 'powerup', position: [5, 2, -6], color: '#22c55e' },
    { id: 3, type: 'powerup', position: [0, 3, -8], color: '#4a90e2' },
  ], [])

  const collectibles: GameElement[] = useMemo(() => [
    { id: 1, type: 'collectible', position: [-3, 1.8, -7], color: '#fcd34d' },
    { id: 2, type: 'collectible', position: [3, 1.8, -7], color: '#a78bfa' },
    { id: 3, type: 'collectible', position: [-1, 2.5, -11], color: '#22d3ee' },
    { id: 4, type: 'collectible', position: [1, 2.5, -11], color: '#fcd34d' },
  ], [])

  const portals: GameElement[] = useMemo(() => [
    { id: 1, type: 'portal', position: [-9, 1, -18], color: '#8b5cf6' },
    { id: 2, type: 'portal', position: [9, 1, -18], color: '#06b6d4' },
  ], [])

  useEffect(() => {
    enemiesRef.current = targets
      .filter(t => ['enemy', 'boss', 'minion'].includes(t.type))
      .map(t => ({
        id: t.id,
        position: new THREE.Vector3(...t.position),
        targetPosition: new THREE.Vector3(Math.random() * 10 - 5, 1.5, Math.random() * -10 - 5),
        health: t.health || 100,
        maxHealth: t.health || 100,
        speed: t.type === 'boss' ? 0.01 : t.type === 'enemy' ? 0.02 : 0.03,
        attackCooldown: t.type === 'boss' ? 2000 : t.type === 'enemy' ? 1500 : 1000,
        lastAttackTime: 0
      }))
  }, [])

  const handleShoot = useCallback(() => {
    if (!camera) return
    
    const cameraPosition = new THREE.Vector3()
    camera.getWorldPosition(cameraPosition)
    
    const direction = new THREE.Vector3()
    camera.getWorldDirection(direction)
    
    const newBullet: BulletData = {
      id: bulletIdCounter.current++,
      position: cameraPosition.clone().add(direction.clone().multiplyScalar(0.5)),
      velocity: direction.clone().multiplyScalar(20),
      damage: 25
    }
    
    bulletsRef.current.push(newBullet)
    setBullets([...bulletsRef.current])
  }, [camera])

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.code === 'Space') {
        event.preventDefault()
        handleShoot()
      }
    }
    
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleShoot])

  const handleBulletUpdate = useCallback((bulletId: number, position: THREE.Vector3) => {
    for (const target of targets) {
      if (hitTargets.has(target.id)) continue
      
      const targetPos = new THREE.Vector3(...target.position)
      const distance = position.distanceTo(targetPos)
      
      if (distance < 0.8) {
        setHitTargets(prev => new Set([...prev, target.id]))
        
        setExplosions(prev => [...prev, {
          id: explosionIdCounter.current++,
          position: [...target.position] as [number, number, number],
          color: target.color
        }])
        
        setTimeout(() => {
          setExplosions(prev => prev.filter(e => e.id !== explosionIdCounter.current - 1))
        }, 800)
        
        onTargetHit?.(target.id, target.points || 10)
        onScoreChange?.(10)
        
        bulletsRef.current = bulletsRef.current.filter(b => b.id !== bulletId)
        setBullets([...bulletsRef.current])
        break
      }
    }
    
    bulletsRef.current = bulletsRef.current.filter(b => b.id !== bulletId)
    setBullets([...bulletsRef.current])
  }, [targets, hitTargets, onTargetHit, onScoreChange])

  useFrame((state) => {
    const now = state.clock.elapsedTime * 1000
    
    enemiesRef.current.forEach(enemy => {
      const playerPos = new THREE.Vector3(0, 0, 0)
      const distanceToPlayer = enemy.position.distanceTo(playerPos)
      
      if (distanceToPlayer > 3) {
        enemy.position.lerp(playerPos, enemy.speed)
      } else {
        if (now - enemy.lastAttackTime > enemy.attackCooldown) {
          onHealthChange?.(Math.max(0, health - 10))
          enemy.lastAttackTime = now
        }
      }
      
      if (Math.random() < 0.02) {
        enemy.targetPosition = new THREE.Vector3(
          Math.random() * 16 - 8,
          1.5,
          Math.random() * -10 - 8
        )
      }
      
      enemy.position.lerp(enemy.targetPosition, 0.01)
    })
  })

  return (
    <>
      <ambientLight intensity={0.4} />
      <directionalLight position={[10, 10, 5]} intensity={1.5} castShadow />
      <pointLight position={[0, 5, 0]} intensity={0.8} color="#8b5cf6" />
      <pointLight position={[-5, 3, -5]} intensity={0.5} color="#ef4444" />
      <pointLight position={[5, 3, -5]} intensity={0.5} color="#22c55e" />
      <pointLight position={[-9, 2, -17]} intensity={0.6} color="#8b5cf6" />
      <pointLight position={[9, 2, -17]} intensity={0.6} color="#06b6d4" />

      <Sky sunPosition={[100, 20, 100]} turbidity={0.5} rayleigh={0.5} />
      <Stars radius={150} depth={80} count={3000} factor={5} saturation={0} fade speed={1.5} />

      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -2, 0]} receiveShadow>
        <planeGeometry args={[60, 60]} />
        <meshStandardMaterial color="#1e293b" />
      </mesh>

      <mesh position={[0, -1, 0]}>
        <boxGeometry args={[60, 2, 60]} />
        <meshStandardMaterial color="#334155" />
      </mesh>

      <mesh position={[0, -0.5, -25]}>
        <boxGeometry args={[40, 5, 0.5]} />
        <meshStandardMaterial color="#1e3a5f" />
      </mesh>

      {obstacles.map(obstacle => (
        <Obstacle key={obstacle.id} position={obstacle.position} color={obstacle.color} />
      ))}

      {powerups.map((powerup, index) => {
        const types: Array<'star' | 'shield' | 'speed' | 'health'> = ['star', 'speed', 'shield', 'health']
        return (
          <PowerUp
            key={powerup.id}
            position={powerup.position}
            type={types[index % types.length]}
            onClick={() => {
              if (types[index % types.length] === 'health') {
                onHealthChange?.(Math.min(100, (health || 100) + 30))
              } else if (types[index % types.length] === 'star') {
                onScoreChange?.(50)
              }
            }}
          />
        )
      })}

      {collectibles.map((collectible, index) => {
        const types: Array<'coin' | 'gem' | 'crystal'> = ['coin', 'gem', 'crystal']
        return (
          <Collectible
            key={collectible.id}
            position={collectible.position}
            type={types[index % types.length]}
            onClick={() => onScoreChange?.(types[index % types.length] === 'crystal' ? 30 : types[index % types.length] === 'gem' ? 20 : 10)}
          />
        )
      })}

      {portals.map(portal => (
        <Portal
          key={portal.id}
          position={portal.position}
          color={portal.color}
        />
      ))}

      {targets.map(target => {
        if (hitTargets.has(target.id)) return null
        
        if (target.type === 'target') {
          return (
            <Target
              key={target.id}
              position={target.position}
              color={target.color}
              emoji={target.emoji}
              points={target.points}
              onClick={() => {
                setHitTargets(prev => new Set([...prev, target.id]))
                setExplosions(prev => [...prev, {
                  id: explosionIdCounter.current++,
                  position: [...target.position] as [number, number, number],
                  color: target.color
                }])
                onTargetHit?.(target.id, target.points || 10)
                onScoreChange?.(10)
              }}
            />
          )
        } else if (target.type === 'enemy') {
          const enemyData = enemiesRef.current.find(e => e.id === target.id)
          return (
            <Enemy
              key={target.id}
              position={target.position}
              color={target.color}
              emoji={target.emoji}
              points={target.points}
              health={enemyData?.health || target.health}
              maxHealth={target.health || 100}
              onClick={() => {
                if (enemyData) {
                  enemyData.health -= 25
                  if (enemyData.health <= 0) {
                    setHitTargets(prev => new Set([...prev, target.id]))
                    setExplosions(prev => [...prev, {
                      id: explosionIdCounter.current++,
                      position: [...target.position] as [number, number, number],
                      color: target.color
                    }])
                    onScoreChange?.(target.points || 25)
                  }
                }
              }}
            />
          )
        } else if (target.type === 'boss') {
          const enemyData = enemiesRef.current.find(e => e.id === target.id)
          return (
            <Boss
              key={target.id}
              position={target.position}
              color={target.color}
              emoji={target.emoji}
              points={target.points}
              health={enemyData?.health || target.health}
              maxHealth={target.health || 500}
              onClick={() => {
                if (enemyData) {
                  enemyData.health -= 25
                  if (enemyData.health <= 0) {
                    setHitTargets(prev => new Set([...prev, target.id]))
                    setExplosions(prev => [...prev, {
                      id: explosionIdCounter.current++,
                      position: [...target.position] as [number, number, number],
                      color: target.color
                    }])
                    onScoreChange?.(target.points || 100)
                  }
                }
              }}
            />
          )
        } else if (target.type === 'minion') {
          const enemyData = enemiesRef.current.find(e => e.id === target.id)
          return (
            <Minion
              key={target.id}
              position={target.position}
              color={target.color}
              emoji={target.emoji}
              points={target.points}
              health={enemyData?.health || target.health}
              maxHealth={target.health || 50}
              onClick={() => {
                if (enemyData) {
                  enemyData.health -= 25
                  if (enemyData.health <= 0) {
                    setHitTargets(prev => new Set([...prev, target.id]))
                    setExplosions(prev => [...prev, {
                      id: explosionIdCounter.current++,
                      position: [...target.position] as [number, number, number],
                      color: target.color
                    }])
                    onScoreChange?.(target.points || 15)
                  }
                }
              }}
            />
          )
        }
        return null
      })}

      {explosions.map(explosion => (
        <Explosion
          key={explosion.id}
          position={explosion.position}
          color={explosion.color}
          scale={targets.find(t => t.id === explosion.id)?.type === 'boss' ? 2 : 1}
        />
      ))}

      {bullets.map(bullet => (
        <Bullet
          key={bullet.id}
          position={bullet.position}
          velocity={bullet.velocity}
          onUpdate={(pos) => handleBulletUpdate(bullet.id, pos)}
          onDestroy={() => {
            bulletsRef.current = bulletsRef.current.filter(b => b.id !== bullet.id)
            setBullets([...bulletsRef.current])
          }}
        />
      ))}

      <PlayerAvatar onHealthChange={onHealthChange} health={health} />
      
      <Html position={[0, -1.5, -2]} center>
        <div className="flex flex-col items-center gap-2 text-white/80 text-sm">
          <div className="flex items-center gap-4">
            <span>🎯 点击目标或按空格键射击</span>
          </div>
          <div className="flex items-center gap-4">
            <span>⭐ 收集道具获得分数</span>
            <span>❤️ 收集红心恢复生命</span>
          </div>
        </div>
      </Html>
    </>
  )
}

export default function GameScene({
  questionIndex,
  isCorrect,
  showFeedback,
  levelName = '射击训练场',
  onTargetHit,
  enableVR = false,
  score = 0,
  health = 100,
  onScoreChange,
  onHealthChange
}: GameSceneProps) {
  const [showLevelTitle, setShowLevelTitle] = useState(true)
  const [showAchievement, setShowAchievement] = useState(false)
  const [achievementText, setAchievementText] = useState('')
  const [isVRSupported, setIsVRSupported] = useState(false)
  const [isVRActive, setIsVRActive] = useState(false)
  const [currentScore, setCurrentScore] = useState(score)
  const [currentHealth, setCurrentHealth] = useState(health)

  const cameraPosition = useMemo(() => {
    const positions = [
      [0, 2, 5],
      [2, 2, 5],
      [-2, 2, 5],
      [0, 3, 6],
      [3, 2, 4],
    ]
    return positions[questionIndex % positions.length]
  }, [questionIndex])

  useEffect(() => {
    if (navigator.xr) {
      navigator.xr.isSessionSupported('immersive-vr').then(supported => {
        setIsVRSupported(supported)
      })
    }
  }, [])

  useEffect(() => {
    setShowLevelTitle(true)
    const timer = setTimeout(() => setShowLevelTitle(false), 2000)
    return () => clearTimeout(timer)
  }, [questionIndex])

  useEffect(() => {
    if (isCorrect && showFeedback) {
      const achievements = [
        '完美回答！+10',
        '太棒了！连续正确！',
        '知识达人！',
        '射击天才！',
        'BOOM！爆头！'
      ]
      setAchievementText(achievements[Math.floor(Math.random() * achievements.length)])
      setShowAchievement(true)
    }
  }, [isCorrect, showFeedback])

  const handleScoreChange = (points: number) => {
    setCurrentScore(prev => prev + points)
    onScoreChange?.(points)
  }

  const handleHealthChange = (newHealth: number) => {
    setCurrentHealth(newHealth)
    onHealthChange?.(newHealth)
  }

  return (
    <div className="relative w-full h-full">
      <Canvas
        camera={{ position: cameraPosition as [number, number, number], fov: 60 }}
        style={{ background: 'linear-gradient(to bottom, #0f172a, #1e293b)' }}
        shadows
        vr={enableVR && isVRSupported}
      >
        {!isVRActive ? (
          <OrbitControls enableZoom={true} enablePan={false} minDistance={3} maxDistance={12} />
        ) : null}
        <ShootingRange 
          onTargetHit={onTargetHit}
          onScoreChange={handleScoreChange}
          onHealthChange={handleHealthChange}
          health={currentHealth}
        />
        <LevelTitle text={levelName} show={showLevelTitle} />
        <FeedbackEffect isCorrect={isCorrect} show={showFeedback} />
        <AchievementEffect
          text={achievementText}
          show={showAchievement}
          onComplete={() => setShowAchievement(false)}
        />
      </Canvas>
      
      <div className="absolute top-4 left-4 z-10">
        <div className="bg-gray-900/80 backdrop-blur-sm rounded-xl p-4 text-white">
          <div className="flex items-center gap-4">
            <div>
              <p className="text-xs text-gray-400">得分</p>
              <p className="text-2xl font-bold text-yellow-400">{currentScore}</p>
            </div>
            <div className="w-px h-10 bg-gray-700" />
            <div>
              <p className="text-xs text-gray-400">生命</p>
              <div className="flex items-center gap-1">
                {Array.from({ length: 10 }).map((_, i) => (
                  <span key={i} className={`text-lg ${i < Math.floor(currentHealth / 10) ? 'opacity-100' : 'opacity-30'}`}>
                    ❤️
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {enableVR && isVRSupported && (
        <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 z-10">
          <button
            onClick={() => setIsVRActive(!isVRActive)}
            className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-xl font-medium hover:from-purple-700 hover:to-indigo-700 transition-all shadow-lg"
          >
            <span className="text-xl">🥽</span>
            {isVRActive ? '退出VR' : '进入VR模式'}
          </button>
        </div>
      )}
      
      {enableVR && !isVRSupported && (
        <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 z-10">
          <div className="flex items-center gap-2 px-4 py-2 bg-gray-800/80 text-gray-300 rounded-xl text-sm backdrop-blur-sm">
            <span className="text-xl">🥽</span>
            <span>VR不支持，请使用支持WebXR的浏览器</span>
          </div>
        </div>
      )}
    </div>
  )
}
