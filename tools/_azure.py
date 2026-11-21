import json
import subprocess

import config


def use_fixtures() -> bool:
    """Return True when tools should read local JSON fixtures instead of calling Azure CLI."""
    return config.USE_FIXTURES


def run_az(args: list[str], timeout: int | None = None) -> list | dict:
    """Run an Azure CLI command and return parsed JSON, or {"error": ...} on failure."""
    cmd = ["az", *args, "-o", "json"]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout or config.AZ_TIMEOUT,
        )
    except FileNotFoundError:
        return {"error": "Azure CLI ('az') not found on PATH."}
    except subprocess.TimeoutExpired:
        return {"error": f"Azure CLI command timed out: {' '.join(cmd[:4])}"}
    except OSError as e:
        return {"error": f"Failed to run Azure CLI: {e}"}

    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "unknown error").strip()
        return {"error": f"Azure CLI error: {detail}"}

    output = proc.stdout.strip()
    if not output:
        return []

    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON returned by Azure CLI."}


def get_openai_auth_token() -> tuple[str | None, str | None]:
    """Fetch a bearer token for Azure OpenAI via Managed Identity / Azure CLI.

    Returns (token, error).
    """
    result = run_az([
        "account", "get-access-token",
        "--resource", "https://cognitiveservices.azure.com",
    ])
    if isinstance(result, dict) and "accessToken" in result:
        return result["accessToken"], None
    err = result.get("error") if isinstance(result, dict) else "Unexpected token response"
    return None, err


def get_key_vault_secret(vault_name: str, secret_name: str) -> tuple[str | None, str | None]:
    """Fetch a secret from Azure Key Vault via Azure CLI.

    Returns (value, error).
    """
    result = run_az([
        "keyvault", "secret", "show",
        "--vault-name", vault_name,
        "--name", secret_name,
    ])
    if isinstance(result, dict) and "value" in result:
        return result["value"], None
    err = result.get("error") if isinstance(result, dict) else "Unexpected Key Vault response"
    return None, err
