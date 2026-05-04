from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel
from datetime import datetime
import os
import re

try:
    from pdfplumber import open as open_pdf
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from pptx import Presentation
    PPT_AVAILABLE = True
except ImportError:
    PPT_AVAILABLE = False

from apps.core.database import SessionLocal
from apps.core.models import Course, Level, Question, QuestionType
from apps.core.level_engine import LevelContext, Task, Achievement, AchievementType, AchievementRarity


class ImportSourceType(str, Enum):
    PDF = "pdf"
    PPT = "ppt"
    PPTX = "pptx"
    TEXT = "text"


class ParsedSection(BaseModel):
    title: str
    content: str
    level: int = 1


class ImportResult(BaseModel):
    success: bool
    message: str
    course_id: Optional[int] = None
    levels_created: int = 0
    questions_created: int = 0
    warnings: List[str] = []


class ContentImporter:
    def __init__(self):
        self._db = None  # 不在构造时持有会话，避免陈旧连接

    def _open_session(self):
        """Every public call must open a fresh session and close in finally."""
        return SessionLocal()

    def _extract_text_from_pdf(self, file_path: str) -> str:
        """从PDF文件中提取文本"""
        if not PDF_AVAILABLE:
            raise ImportError("pdfplumber库未安装，请运行: pip install pdfplumber")
        
        text = ""
        with open_pdf(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n"
        return text

    def _extract_text_from_ppt(self, file_path: str) -> str:
        """从PPT/PPTX文件中提取文本"""
        if not PPT_AVAILABLE:
            raise ImportError("python-pptx库未安装，请运行: pip install python-pptx")
        
        prs = Presentation(file_path)
        text = ""
        
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text += shape.text + "\n"
            text += "\n\n"
        
        return text

    def _parse_text_to_sections(self, text: str) -> List[ParsedSection]:
        """将文本解析为结构化章节"""
        sections = []
        lines = text.split('\n')
        
        current_section = None
        current_content = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 检测标题（以数字开头或特定格式）
            title_match = re.match(r'^(\d+[\.\-])+\s+(.+)$', line)
            if title_match:
                if current_section:
                    current_section.content = '\n'.join(current_content).strip()
                    sections.append(current_section)
                level = len(title_match.group(1).split('.'))
                current_section = ParsedSection(
                    title=title_match.group(2).strip(),
                    content="",
                    level=level
                )
                current_content = []
            elif current_section:
                current_content.append(line)
        
        if current_section:
            current_section.content = '\n'.join(current_content).strip()
            sections.append(current_section)
        
        return sections

    def _generate_questions_from_section(self, section: ParsedSection) -> List[Dict[str, Any]]:
        """从章节内容生成问题"""
        questions = []
        content = section.content
        
        # 生成选择题
        if len(content) > 50:
            questions.append({
                "type": QuestionType.SINGLE_CHOICE,
                "content": f"关于「{section.title}」，以下说法正确的是？",
                "options": ["选项A", "选项B", "选项C", "选项D"],
                "correct_answer": "选项A",
                "explanation": f"本题考查「{section.title}」的相关知识",
                "difficulty": min(section.level + 1, 5)
            })
        
        # 生成判断题
        if len(content) > 30:
            questions.append({
                "type": QuestionType.TRUE_FALSE,
                "content": f"判断题：{section.title}是学习内容的重要组成部分",
                "options": None,
                "correct_answer": True,
                "explanation": f"本题考查对「{section.title}」的理解",
                "difficulty": min(section.level, 3)
            })
        
        # 生成填空题（如果内容中有明显的概念）
        concept_pattern = r'([\u4e00-\u9fa5a-zA-Z0-9]+)[\u3002。，,、]'
        matches = re.findall(concept_pattern, content[:500])
        if len(matches) >= 3:
            questions.append({
                "type": QuestionType.FILL_BLANK,
                "content": f"______是{section.title}中的核心概念之一",
                "options": None,
                "correct_answer": matches[0],
                "explanation": f"本题考查「{section.title}」中的核心概念",
                "difficulty": min(section.level + 1, 4)
            })
        
        return questions

    def import_from_file(
        self,
        file_path: str,
        source_type: ImportSourceType,
        course_id: Optional[int] = None,
        course_name: Optional[str] = None
    ) -> ImportResult:
        """从文件导入内容并生成关卡"""
        self._db = self._open_session()
        try:
            # 提取文本
            if source_type in [ImportSourceType.PDF]:
                text = self._extract_text_from_pdf(file_path)
            elif source_type in [ImportSourceType.PPT, ImportSourceType.PPTX]:
                text = self._extract_text_from_ppt(file_path)
            else:
                return ImportResult(
                    success=False,
                    message=f"不支持的文件类型: {source_type}"
                )
            
            if not text.strip():
                return ImportResult(
                    success=False,
                    message="文件内容为空"
                )
            
            # 解析章节
            sections = self._parse_text_to_sections(text)
            
            if not sections:
                return ImportResult(
                    success=False,
                    message="未能解析出章节内容"
                )
            
            # 创建或获取课程
            if course_id:
                course = self._db.query(Course).filter(Course.id == course_id).first()
                if not course:
                    return ImportResult(
                        success=False,
                        message=f"课程ID {course_id} 不存在"
                    )
            elif course_name:
                course = Course(
                    name=course_name,
                    description=f"从{source_type.value.upper()}文件导入的课程",
                    status="draft"
                )
                self._db.add(course)
                self._db.commit()
                self._db.refresh(course)
                course_id = course.id
            else:
                return ImportResult(
                    success=False,
                    message="必须提供course_id或course_name"
                )
            
            warnings = []
            levels_created = 0
            questions_created = 0
            
            # 按章节创建关卡和问题
            for section in sections:
                # 创建关卡
                level = Level(
                    course_id=course_id,
                    name=section.title,
                    description=section.content[:200] + "..." if len(section.content) > 200 else section.content,
                    order=len(self._db.query(Level).filter(Level.course_id == course_id).all()) + 1,
                    max_score=100,
                    config={"game_mode": "quiz", "time_limit": 300}
                )
                self._db.add(level)
                self._db.commit()
                self._db.refresh(level)
                levels_created += 1
                
                # 生成问题
                questions = self._generate_questions_from_section(section)
                for q_data in questions:
                    question = Question(
                        level_id=level.id,
                        type=q_data["type"],
                        content=q_data["content"],
                        options=q_data["options"],
                        correct_answer=q_data["correct_answer"],
                        explanation=q_data["explanation"],
                        difficulty=q_data["difficulty"]
                    )
                    self._db.add(question)
                    questions_created += 1
                
                if not questions:
                    warnings.append(f"章节「{section.title}」未能生成问题")
            
            self._db.commit()
            
            return ImportResult(
                success=True,
                message=f"成功导入！创建了 {levels_created} 个关卡和 {questions_created} 个问题",
                course_id=course_id,
                levels_created=levels_created,
                questions_created=questions_created,
                warnings=warnings
            )
        
        except Exception as e:
            self._db.rollback()
            return ImportResult(
                success=False,
                message=f"导入失败: {str(e)}"
            )
        finally:
            self._db.close()
            self._db = None

    def import_from_text(
        self,
        text: str,
        course_id: Optional[int] = None,
        course_name: Optional[str] = None
    ) -> ImportResult:
        """从文本直接导入内容"""
        self._db = self._open_session()
        try:
            if not text.strip():
                return ImportResult(
                    success=False,
                    message="文本内容为空"
                )
            
            # 解析章节
            sections = self._parse_text_to_sections(text)
            
            if not sections:
                return ImportResult(
                    success=False,
                    message="未能解析出章节内容"
                )
            
            # 创建或获取课程
            if course_id:
                course = self._db.query(Course).filter(Course.id == course_id).first()
                if not course:
                    return ImportResult(
                        success=False,
                        message=f"课程ID {course_id} 不存在"
                    )
            elif course_name:
                course = Course(
                    name=course_name,
                    description="从文本导入的课程",
                    status="draft"
                )
                self._db.add(course)
                self._db.commit()
                self._db.refresh(course)
                course_id = course.id
            else:
                return ImportResult(
                    success=False,
                    message="必须提供course_id或course_name"
                )
            
            warnings = []
            levels_created = 0
            questions_created = 0
            
            for section in sections:
                level = Level(
                    course_id=course_id,
                    name=section.title,
                    description=section.content[:200] + "..." if len(section.content) > 200 else section.content,
                    order=len(self._db.query(Level).filter(Level.course_id == course_id).all()) + 1,
                    max_score=100,
                    config={"game_mode": "quiz", "time_limit": 300}
                )
                self._db.add(level)
                self._db.commit()
                self._db.refresh(level)
                levels_created += 1
                
                questions = self._generate_questions_from_section(section)
                for q_data in questions:
                    question = Question(
                        level_id=level.id,
                        type=q_data["type"],
                        content=q_data["content"],
                        options=q_data["options"],
                        correct_answer=q_data["correct_answer"],
                        explanation=q_data["explanation"],
                        difficulty=q_data["difficulty"]
                    )
                    self._db.add(question)
                    questions_created += 1
                
                if not questions:
                    warnings.append(f"章节「{section.title}」未能生成问题")
            
            self._db.commit()
            
            return ImportResult(
                success=True,
                message=f"成功导入！创建了 {levels_created} 个关卡和 {questions_created} 个问题",
                course_id=course_id,
                levels_created=levels_created,
                questions_created=questions_created,
                warnings=warnings
            )
        
        except Exception as e:
            self._db.rollback()
            return ImportResult(
                success=False,
                message=f"导入失败: {str(e)}"
            )
        finally:
            self._db.close()
            self._db = None

    def generate_level_context(self, level_id: int) -> Optional[LevelContext]:
        """从数据库生成关卡上下文"""
        db = self._open_session()
        try:
            db_level = db.query(Level).filter(Level.id == level_id).first()
            if not db_level:
                return None

            questions = db.query(Question).filter(Question.level_id == level_id).all()

            tasks = []
            for q in questions:
                task_type = q.type.value
                tasks.append(Task(
                    id=f"q_{q.id}",
                    type=task_type,
                    content=q.content,
                    points=max(10, 50 - q.difficulty * 8),
                    options=q.options,
                    correct_answer=q.correct_answer
                ))

            achievements = [
                Achievement(
                    id=f"level_{level_id}_perfect",
                    name="完美通关",
                    description=f"在「{db_level.name}」中获得满分",
                    type=AchievementType.SCORE,
                    rarity=AchievementRarity.RARE,
                    condition={"min_score": db_level.max_score},
                    points=50
                ),
                Achievement(
                    id=f"level_{level_id}_first_try",
                    name="初次通关",
                    description=f"第一次尝试就通过「{db_level.name}」",
                    type=AchievementType.COMPLETION,
                    rarity=AchievementRarity.COMMON,
                    condition={},
                    points=20
                )
            ]

            return LevelContext(
                user_id=0,
                level_id=level_id,
                course_id=db_level.course_id,
                tasks=tasks,
                max_score=db_level.max_score,
                achievements=achievements,
                metadata={"time_limit": db_level.config.get("time_limit", 300) if db_level.config else 300}
            )
        finally:
            db.close()


content_importer = ContentImporter()
