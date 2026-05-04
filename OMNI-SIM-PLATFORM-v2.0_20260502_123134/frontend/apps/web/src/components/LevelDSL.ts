export const LevelDSL = {
  VERSION: "2.0",

  schemas: {
    level: {
      type: "object",
      required: ["id", "name", "tasks"],
      properties: {
        id: { type: "string" },
        name: { type: "string" },
        description: { type: "string" },
        type: { type: "string", enum: ["shooting", "puzzle", "adventure", "quiz", "fps_mission"] },
        difficulty: { type: "integer", minimum: 1, maximum: 5 },
        max_score: { type: "integer", default: 100 },
        time_limit: { type: "integer" },
        // FPS Mission DSL v1 — when present (or when type === "fps_mission"),
        // the platform launches the FPS bundle iframe with ?missionPack=<id>.
        // The mission JSON itself lives at backend/static/game/missions/<id>.json
        // and fully specifies intro video / scene / acts / E-key interactables /
        // narration / scoring — replacing the hardcoded SmartX V2V content.
        mission_pack: { type: "string" },
        tasks: {
          type: "array",
          items: { $ref: "#/schemas/task" }
        },
        dialogue_nodes: {
          type: "array",
          items: { $ref: "#/schemas/dialogue_node" }
        },
        scene_elements: {
          type: "array",
          items: { $ref: "#/schemas/scene_element" }
        },
        npcs: {
          type: "array",
          items: { $ref: "#/schemas/npc" }
        },
        rewards: {
          type: "object",
          properties: {
            experience: { type: "integer" },
            coins: { type: "integer" },
            items: { type: "array", items: { type: "string" } }
          }
        }
      }
    },

    task: {
      type: "object",
      required: ["id", "type", "content"],
      properties: {
        id: { type: "string" },
        type: {
          type: "string",
          enum: ["single_choice", "multiple_choice", "true_false", "fill_blank", "drag_drop", "shooting"]
        },
        content: { type: "string" },
        options: {
          type: "array",
          items: { type: "string" }
        },
        correct_answer: { type: ["string", "array", "boolean"] },
        explanation: { type: "string" },
        difficulty: { type: "integer", minimum: 1, maximum: 3 },
        points: { type: "integer", default: 10 },
        required: { type: "boolean", default: true },
        hint: { type: "string" }
      }
    },

    dialogue_node: {
      type: "object",
      required: ["id", "text"],
      properties: {
        id: { type: "string" },
        text: { type: "string" },
        responses: {
          type: "array",
          items: {
            type: "object",
            properties: {
              text: { type: "string" },
              nextId: { type: ["string", "null"] }
            }
          }
        },
        type: { type: "string", enum: ["start", "normal", "end"] },
        position: {
          type: "object",
          properties: {
            x: { type: "number" },
            y: { type: "number" }
          }
        }
      }
    },

    scene_element: {
      type: "object",
      required: ["id", "type"],
      properties: {
        id: { type: "string" },
        type: { type: "string", enum: ["target", "enemy", "obstacle", "powerup", "collectible"] },
        name: { type: "string" },
        position: {
          type: "object",
          properties: {
            x: { type: "number" },
            y: { type: "number" },
            z: { type: "number" }
          }
        },
        points: { type: "integer" }
      }
    },

    npc: {
      type: "object",
      required: ["id", "name"],
      properties: {
        id: { type: "string" },
        name: { type: "string" },
        role: { type: "string" },
        avatar: { type: "string" },
        position: {
          type: "object",
          properties: {
            x: { type: "number" },
            y: { type: "number" },
            z: { type: "number" }
          }
        }
      }
    }
  }
}

export function validateLevelDSL(levelData: unknown): { valid: boolean; errors: string[] } {
  const errors: string[] = []

  if (!levelData || typeof levelData !== "object") {
    return { valid: false, errors: ["Level data must be an object"] }
  }

  const level = levelData as Record<string, unknown>

  if (!level.id || typeof level.id !== "string") {
    errors.push("Level must have a string 'id' field")
  }

  if (!level.name || typeof level.name !== "string") {
    errors.push("Level must have a string 'name' field")
  }

  if (!level.tasks || !Array.isArray(level.tasks)) {
    errors.push("Level must have an array 'tasks' field")
  } else {
    level.tasks.forEach((task, index) => {
      if (!task.id) {
        errors.push(`Task at index ${index} must have an 'id' field`)
      }
      if (!task.type) {
        errors.push(`Task at index ${index} must have a 'type' field`)
      }
      if (!task.content) {
        errors.push(`Task at index ${index} must have a 'content' field`)
      }
    })
  }

  return { valid: errors.length === 0, errors }
}

export function createLevelTemplate(levelId: string, name: string): object {
  return {
    id: levelId,
    name,
    description: "",
    type: "quiz",
    difficulty: 1,
    max_score: 100,
    tasks: [],
    npcs: [],
    rewards: {
      experience: 50,
      coins: 100,
      items: []
    }
  }
}

export function createTaskTemplate(
  taskId: string,
  type: string,
  content: string
): object {
  const baseTask = {
    id: taskId,
    type,
    content,
    difficulty: 1,
    points: 10,
    required: true
  }

  switch (type) {
    case "single_choice":
      return { ...baseTask, options: ["选项 A", "选项 B", "选项 C", "选项 D"], correct_answer: "选项 A" }
    case "multiple_choice":
      return { ...baseTask, options: ["选项 A", "选项 B", "选项 C"], correct_answer: ["选项 A", "选项 B"] }
    case "true_false":
      return { ...baseTask, correct_answer: true }
    case "fill_blank":
      return { ...baseTask, correct_answer: "" }
    default:
      return baseTask
  }
}
