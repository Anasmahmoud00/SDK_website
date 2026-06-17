#!/usr/bin/env python3
import os
import sys
import argparse

# Required environment variables for various modes
REQUIRED_VARS = {
    "common": [
        "DATABASE_URL",
        "REDIS_URL",
        "ENV",
    ],
    "production": [
        "CORS_ALLOWED_ORIGINS",
        "KAGGLE_OCR_URL",
        "COHERE_API_KEY",
        "OCI_REGION",
        "JWT_SECRET_KEY",
        "LIVEKIT_URL",
    ],
    "ai_engines": [
        "OLLAMA_HOST",
        "OLLAMA_MODEL",
    ],
}


def check_env(env_name: str) -> bool:
    print(f"--- Validating Environment: {env_name} ---")

    missing = []

    # Check common vars
    for var in REQUIRED_VARS["common"]:
        if not os.getenv(var):
            missing.append(var)

    # Check production specific vars
    if env_name == "production":
        for var in REQUIRED_VARS["production"]:
            if not os.getenv(var):
                missing.append(var)

    # Check engine vars (warn if missing, might use defaults)
    for var in REQUIRED_VARS["ai_engines"]:
        if not os.getenv(var):
            print(f"[WARN] Optional engine variable {var} not set. Using framework defaults.")

    if missing:
        print(f"[ERROR] Missing required environment variables for {env_name}:")
        for m in missing:
            print(f"  - {m}")
        return False

    print(f"[OK] All required variables for {env_name} are present.")
    return True


def main():
    parser = argparse.ArgumentParser(description="Validate Narrative AI environment variables.")
    parser.add_argument("--env", choices=["development", "production", "test"], default="development")
    args = parser.parse_args()
    # Prefer CLI --env so that "validate_env.py --env production" always validates production
    target_env = args.env
    success = check_env(target_env)

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
