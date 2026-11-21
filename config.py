import os
from dotenv import load_dotenv

load_dotenv()  # reads the .env file

ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini")
MAX_STEPS = int(os.getenv("MAX_STEPS", "12"))  # the loop can never run more than this many model calls
USE_FIXTURES = os.getenv("USE_FIXTURES", "false").lower() in ("1", "true", "yes")
FIXTURES_DIR = os.getenv("FIXTURES_DIR", "")  # optional override (used by eval harness)
AZ_TIMEOUT = int(os.getenv("AZ_TIMEOUT", "30"))

# Cloud auth (optional): Managed Identity and/or Azure Key Vault
USE_MANAGED_IDENTITY = os.getenv("AZURE_USE_MANAGED_IDENTITY", "false").lower() in ("1", "true", "yes")
KEY_VAULT_NAME = os.getenv("AZURE_KEY_VAULT_NAME", "")
KEY_VAULT_SECRET_NAME = os.getenv("AZURE_KEY_VAULT_SECRET_NAME", "azure-openai-api-key")
