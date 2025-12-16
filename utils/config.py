from pydantic_settings import BaseSettings, SettingsConfigDict



class Settings(BaseSettings):
    # Database
    mongo_uri: str

    # JWT
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # OTP
    totp_issuer: str = "AgroGPT"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()

MODEL_URLS = {
    "binary_classifier": {
        "url": "https://drive.google.com/drive/folders/1QuLVfkkIT-tcVWdxj-oqDdIN7qZ1HT80?usp=sharing",
        "path": "binary_classification/agro_classifier_FINAL_CLEAN.keras"
    },
    "merged_model": {
        "files": {
            "model-00002-of-00002.safetensors": "1OtFFr41VLeaUbA4Ij2ofOLIpiRSXX0sl",
            "model.safetensors.index.json": "1SzIrWiNvM0amOEFxGztORwrlXz7jlhOq",
            "tokenizer.json": "1LKkLnGtea5RGtaDJ5Euziror7nOExvcp",
            "tokenizer_config.json": "1Ig1w9G3-Y9AKZk1g_HFjncEWG9wzE_OO",
            "config.json": "1PV2kg5IGV5GHxk4fBQQhzEQF58LhOW8a",
            "generation_config.json": "1XdnEaY7vCA7ZHMSxiNeHjDRSoBg79Rwp",
            "vocab.json": "1A11NPrMIOASnPvKk9gxbt-PhNv0zfZqb",
            "merges.txt": "1vc8bqXr-_W5Hy9znhTNAOU3602UBlMnS",
            "special_tokens_map.json": "1-Lfj7WqHopcG52mCTnFkM4GpiKeOQ3sa",
            "added_tokens.json": "1uFaScuAJe5Q3UL9sFwqQCRyWf9ROSpos",
        },
        "dir": "merged_model"
    }
}
