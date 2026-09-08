from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# PHP-style hash (from .env) - $2y$ is PHP bcrypt
php_hash = "$2y$12$vtGQWoFP/oVWzUA1pHW0ueCvSkAI1XuOdKi7FddyhrrPGEEhPjTGK"

# Convert $2y$ to $2b$ (PHP to Python bcrypt compatibility)
python_hash = php_hash.replace("$2y$", "$2b$", 1)

print(f"Original hash: {php_hash}")
print(f"Converted hash: {python_hash}")
print(f"Testing password 'admin'...")

try:
    result = pwd_context.verify("admin", python_hash)
    print(f"Password verification result: {result}")
    if result:
        print("✓ Password 'admin' matches the hash!")
    else:
        print("✗ Password 'admin' does NOT match the hash")
except Exception as e:
    print(f"Error: {e}")
