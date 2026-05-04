from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    POSTGRES_USER: str = "admin"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "game_training"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    REDIS_URL: str = "redis://localhost:6379/0"

    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    CLAUDE_API_KEY: str | None = None
    CLAUDE_API_URL: str = "https://api.anthropic.com/v1/messages"
    CLAUDE_MODEL: str = "claude-3-sonnet-20240229"

    QIANWEN_API_KEY: str | None = None
    QIANWEN_API_URL: str = "https://dashscope.aliyuncs.com/api/text/generation"
    QIANWEN_MODEL: str = "qwen-turbo"

    DEEPSEEK_API_KEY: str | None = None
    DEEPSEEK_API_URL: str = "https://api.deepseek.com/v1/chat/completions"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    DEFAULT_AI_MODEL: str = "claude"

    APP_NAME: str = "游戏化培训平台 2.0"
    APP_ENV: str = "development"
    APP_PORT: int = 8000

    USE_SQLITE: bool = True

    # Vector Database Configuration
    VECTOR_DB_HOST: str = "localhost"
    VECTOR_DB_PORT: int = 6333
    VECTOR_DB_API_KEY: str | None = None
    VECTOR_DB_COLLECTION: str = "training_docs"

    # Kafka Configuration
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_GROUP_ID: str = "game_training_group"
    KAFKA_ENABLED: bool = False

    # S3 Storage Configuration
    S3_ENABLED: bool = False
    S3_ACCESS_KEY: str | None = None
    S3_SECRET_KEY: str | None = None
    S3_REGION_NAME: str = "us-east-1"
    S3_BUCKET_NAME: str = "game-training-platform"
    S3_ENDPOINT_URL: str | None = None

    # OpenTelemetry Configuration
    OTEL_ENABLED: bool = False
    OTEL_COLLECTOR_URL: str | None = None

    # OAuth/SSO Configuration
    OAUTH_REDIRECT_URI: str = "http://localhost:3000/oauth/callback"

    # Worker / Scheduler Configuration
    MAX_WORKERS: int = 10
    
    # Google OAuth
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    
    # GitHub OAuth
    GITHUB_CLIENT_ID: str | None = None
    GITHUB_CLIENT_SECRET: str | None = None
    
    # Azure AD OAuth
    AZURE_CLIENT_ID: str | None = None
    AZURE_CLIENT_SECRET: str | None = None

    @property
    def DATABASE_URL(self) -> str:
        if self.USE_SQLITE:
            # 把 SQLite 路径锚定到 backend/ 目录，避免不同 cwd 启动产生多个 .db 文件
            from pathlib import Path
            backend_dir = Path(__file__).resolve().parents[2]
            db_path = backend_dir / "game_training.db"
            return f"sqlite:///{db_path}"
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
