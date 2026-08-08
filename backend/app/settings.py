from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="TAR_", extra="ignore")
    env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    database_url: str = "sqlite:///./tar.db"
    vector_backend: str = "memory"
    ipfs_api_url: str = "http://ipfs:5001"
    ipfs_gateway: str = "http://localhost:8080/ipfs"
    llm_provider: str = "echo"
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = ""
    allowed_origins_raw: str = "http://localhost:3000"
    request_timeout: float = 30

    @property
    def allowed_origins(self) -> list[str]:
        return [x.strip() for x in self.allowed_origins_raw.split(",") if x.strip()]

settings = Settings()
