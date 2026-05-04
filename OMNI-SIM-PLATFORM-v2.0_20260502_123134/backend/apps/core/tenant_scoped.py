from sqlalchemy import inspect
from sqlalchemy.orm import Query
from sqlalchemy.orm.session import Session
from .models import Tenant, User, Course, Level, Question, LevelAttempt, Achievement, LearnerProfile, Memory, LeaderboardEntry, UserScore
from . import tenant_context

TENANT_SCOPED_MODELS = [User, Course, Level, Question, LevelAttempt, Achievement, LearnerProfile, Memory]


def tenant_scoped_query(session: Session, model):
    """创建租户隔离的查询对象"""
    current_tenant_id = tenant_context.get_current_tenant_id()
    
    if model not in TENANT_SCOPED_MODELS:
        return session.query(model)
    
    if not current_tenant_id:
        return session.query(model)
    
    return session.query(model).filter(model.tenant_id == current_tenant_id)


def get_tenant_for_user(user_id: int, session: Session) -> Tenant:
    """获取用户所属的租户"""
    user = session.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    if not user.tenant_id:
        return None
    return session.query(Tenant).filter(Tenant.id == user.tenant_id).first()


def ensure_tenant_scope(model_instance, user: User = None):
    """确保模型实例设置了正确的租户ID"""
    if hasattr(model_instance, 'tenant_id') and model_instance.tenant_id is None:
        if user and user.tenant_id:
            model_instance.tenant_id = user.tenant_id
        else:
            current_tenant_id = tenant_context.get_current_tenant_id()
            if current_tenant_id:
                model_instance.tenant_id = current_tenant_id


class TenantScopedSession:
    """租户隔离的会话包装器"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def query(self, *models):
        """创建租户隔离的查询"""
        if not models:
            return self.session.query()
        
        first_model = models[0]
        if first_model in TENANT_SCOPED_MODELS:
            return tenant_scoped_query(self.session, first_model)
        return self.session.query(*models)
    
    def add(self, instance):
        """添加实例时自动设置租户ID"""
        ensure_tenant_scope(instance)
        self.session.add(instance)
    
    def add_all(self, instances):
        """批量添加实例时自动设置租户ID"""
        for instance in instances:
            ensure_tenant_scope(instance)
        self.session.add_all(instances)
    
    def __getattr__(self, name):
        """委托其他方法给底层session"""
        return getattr(self.session, name)


def get_tenant_scoped_session() -> TenantScopedSession:
    """获取租户隔离的会话"""
    from .database import get_db
    session = next(get_db())
    return TenantScopedSession(session)