"""Print fresh values for NOWBUILDER_SECRET_KEY and NOWBUILDER_ENCRYPTION_KEY."""
import secrets

from cryptography.fernet import Fernet

if __name__ == "__main__":
    print(f"NOWBUILDER_SECRET_KEY={secrets.token_urlsafe(48)}")
    print(f"NOWBUILDER_ENCRYPTION_KEY={Fernet.generate_key().decode()}")
