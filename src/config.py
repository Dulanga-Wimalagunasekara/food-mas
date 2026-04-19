from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # MySQL
    mysql_host: str = "mysql"
    mysql_port: int = 3306
    mysql_user: str = "foodmas"
    mysql_password: str = "foodmas_secret"
    mysql_database: str = "foodmas"

    # Ollama
    ollama_host: str = "http://ollama:11434"
    ollama_model: str = "qwen2.5:7b-instruct"
    ollama_fallback_model: str = "llama3.1:8b-instruct-q5_K_M"

    # LangGraph checkpointer
    checkpoint_db_path: str = "/app/data/checkpoints.db"

    # Observability
    log_level: str = "INFO"
    trace_dir: str = "/app/traces"
    log_dir: str = "/app/logs"

    @property
    def mysql_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )

    @property
    def sqlite_checkpoint_url(self) -> str:
        return f"sqlite:///{self.checkpoint_db_path}"


settings = Settings()
