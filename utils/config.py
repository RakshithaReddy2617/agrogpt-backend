from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MONGO_URL: str = "your_mongo_url_here"
    JWT_SECRET: str = "supersecretjwtkey"  # you can use os.getenv or .env

    class Config:
        env_file = ".env"

settings = Settings()
