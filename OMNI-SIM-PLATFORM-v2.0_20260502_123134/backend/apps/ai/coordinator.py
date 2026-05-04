from typing import Optional, Any
from enum import Enum
import json
from apps.ai.config_manager import ai_config_manager
from apps.ai.workers import document_parser, question_generator, verification_worker, npc_worker, recommendation_worker, evaluation_worker
from apps.core.models import Course, Level, Question, Tenant
from apps.core.database import SessionLocal


class WorkerStage(str, Enum):
    RESEARCH = "research"
    SYNTHESIZE = "synthesize"
    IMPLEMENT = "implement"
    VERIFY = "verify"


class CoordinatorAgent:
    """
    协调器Agent - 负责任务调度和流程协调
    使用统一的 AIConfigManager 进行所有AI调用
    """

    def __init__(self):
        self.stage = WorkerStage.RESEARCH
        self.context = {}

    async def process_document(self, document_content: str, metadata: dict, course_id: Optional[int] = None) -> dict:
        self.context = {
            "document_content": document_content,
            "metadata": metadata,
            "current_stage": self.stage,
            "course_id": course_id
        }

        research_result = await self._call_research_worker()
        self.context["research_result"] = research_result

        self.stage = WorkerStage.SYNTHESIZE
        synthesis_result = await self._call_synthesize_worker()
        self.context["synthesis_result"] = synthesis_result

        self.stage = WorkerStage.IMPLEMENT
        implementation = await self._call_implement_worker()
        self.context["implementation"] = implementation

        self.stage = WorkerStage.VERIFY
        verification = await self._call_verify_worker()
        self.context["verification"] = verification

        if course_id:
            await self._save_to_database(implementation, course_id)

        return {
            "success": verification.get("passed", False),
            "level_data": implementation,
            "questions": implementation.get("questions", []),
            "verification_report": verification
        }

    async def _call_research_worker(self) -> dict:
        document_content = self.context.get("document_content", "")

        research_prompt = f"""
分析以下培训材料，提取关键知识点和学习目标：

文档内容：
{document_content[:8000]}

请以 JSON 格式返回：
{{
  "title": "文档标题（从内容推断）",
  "topics": ["主题1", "主题2", "主题3"],
  "key_concepts": [
    {{"concept": "概念名称", "description": "简要描述"}}
  ],
  "difficulty_assessment": "beginner|medium|advanced",
  "chapters": [
    {{"title": "章节标题", "content": "章节内容摘要"}}
  ],
  "key_phrases": ["关键词1", "关键词2"]
}}
"""

        system_prompt = "你是一个专业的培训课程设计师，负责分析培训材料并生成教学内容。请始终以JSON格式返回结果。"
        result = await ai_config_manager.generate(research_prompt, system_prompt)

        try:
            parsed = json.loads(result)
            return parsed
        except (json.JSONDecodeError, ValueError):
            return {
                "title": "培训课程",
                "topics": ["基础概念", "实践操作"],
                "key_concepts": [],
                "difficulty_assessment": "medium",
                "chapters": [],
                "key_phrases": []
            }

    async def _call_synthesize_worker(self) -> dict:
        research = self.context.get("research_result", {})

        synthesize_prompt = f"""
基于以下研究结果，制定关卡设计方案：

研究结果：
{json.dumps(research, ensure_ascii=False, indent=2)}

请设计一个培训课程的关卡结构，返回 JSON：
{{
  "structure": {{
    "total_levels": 3,
    "chapters": [
      {{
        "chapter_name": "章节名称",
        "levels": [
          {{
            "level_name": "关卡名称",
            "level_description": "关卡描述",
            "game_mode": "shooting",
            "max_score": 100,
            "difficulty": 1
          }}
        ]
      }}
    ]
  }},
  "learning_objectives": ["目标1", "目标2"],
  "narrative_story": "一个简单的剧情故事线，用于游戏关卡引导"
}}
"""

        system_prompt = "你是一个专业的培训课程设计师，负责分析培训材料并生成教学内容。请始终以JSON格式返回结果。"
        result = await ai_config_manager.generate(synthesize_prompt, system_prompt)

        try:
            return json.loads(result)
        except (json.JSONDecodeError, ValueError):
            return {
                "structure": {"total_levels": 3, "chapters": []},
                "learning_objectives": ["完成培训"],
                "narrative_story": "欢迎来到培训课程！"
            }

    async def _call_implement_worker(self) -> dict:
        research = self.context.get("research_result", {})
        synthesis = self.context.get("synthesis_result", {})

        chapters = research.get("chapters", [])
        all_questions = []

        for chapter in chapters:
            content = chapter.get("content", "")
            if content:
                qs = await question_generator.generate(content, num_questions=5, difficulty=research.get("difficulty_assessment", "medium"))
                all_questions.extend(qs)

        return {
            "questions": all_questions,
            "narrative": synthesis.get("narrative_story", ""),
            "npc_dialogues": [],
            "structure": synthesis.get("structure", {}),
            "research_summary": research
        }

    async def _call_verify_worker(self) -> dict:
        implementation = self.context.get("implementation", {})
        questions = implementation.get("questions", [])
        content = self.context.get("document_content", "")

        return await verification_worker.verify(questions, content)

    async def _save_to_database(self, implementation: dict, course_id: int):
        try:
            db = SessionLocal()
            structure = implementation.get("structure", {})
            chapters = structure.get("chapters", [])

            for chapter in chapters:
                levels = chapter.get("levels", [])
                for level_idx, level_data in enumerate(levels):
                    level = Level(
                        course_id=course_id,
                        name=level_data.get("level_name", f"关卡 {level_idx + 1}"),
                        description=level_data.get("level_description", ""),
                        order=level_idx + 1,
                        max_score=level_data.get("max_score", 100),
                        config=level_data
                    )
                    db.add(level)
                    db.commit()
                    db.refresh(level)

                    for q_idx, q_data in enumerate(implementation.get("questions", [])[:5]):
                        question = Question(
                            level_id=level.id,
                            type=q_data.get("type", "single_choice"),
                            content=q_data.get("content", ""),
                            options=q_data.get("options"),
                            correct_answer=q_data.get("correct_answer"),
                            explanation=q_data.get("explanation", ""),
                            difficulty=q_data.get("difficulty", 1)
                        )
                        db.add(question)

                    db.commit()

            db.close()
        except Exception as e:
            print(f"Error saving to database: {e}")


coordinator = CoordinatorAgent()
