from app.config import get_settings
import os
settings = get_settings()
env_key = os.getenv("OPENAI_API_KEY")
print(f"AGENT_MODE: {settings.agent_mode}")
print(f"SPECIALIST_MODEL: {settings.specialist_model}")
print(f"TOOL_MODE: {settings.tool_mode}")
print(f"API_KEY: {settings.openai_api_key}")
print(f"ENV_KEY: {env_key}")