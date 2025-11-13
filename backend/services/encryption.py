import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY").encode()
cipher = Fernet(ENCRYPTION_KEY)

def encryptKey(apiKey: str) -> str:
    return cipher.encrypt(apiKey.encode()).decode()

def decryptKey(encryptedKey: str) -> str:
    return cipher.decrypt(encryptedKey.encode()).decode()