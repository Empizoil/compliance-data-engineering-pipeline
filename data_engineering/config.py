from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = Field(..., env="DATABASE_URL")

    # Embedding API
    gemini_api_key: str = Field(..., env="GEMINI_API_KEY")
    embedding_model: str = Field(default="models/text-embedding-004", env="EMBEDDING_MODEL")
    embedding_dimension: int = Field(default=768, env="EMBEDDING_DIMENSION")

    # Chunking
    chunk_size_tokens: int = Field(default=400, env="CHUNK_SIZE_TOKENS")
    chunk_overlap_tokens: int = Field(default=60, env="CHUNK_OVERLAP_TOKENS")

    # Retrieval
    rule_retrieval_top_k: int = Field(default=5, env="RULE_RETRIEVAL_TOP_K")
    disclosure_similarity_threshold: float = Field(default=0.78, env="DISCLOSURE_SIMILARITY_THRESHOLD")
    precedent_top_k: int = Field(default=3, env="PRECEDENT_TOP_K")

    # Operational
    max_file_size_bytes: int = Field(default=10 * 1024 * 1024, env="MAX_FILE_SIZE_BYTES")  # 10 MB
    embedding_batch_size: int = Field(default=20, env="EMBEDDING_BATCH_SIZE")

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
                                 
                                 
                                 