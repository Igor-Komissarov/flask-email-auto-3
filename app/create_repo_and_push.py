import os
import base64
import subprocess
import sys
import requests
from dotenv import load_dotenv
from nacl import encoding, public

# === Настройка окружения ===
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)
load_dotenv()

TOKEN = os.getenv("GITHUB_TOKEN")
USERNAME = os.getenv("GITHUB_USERNAME")
API_URL = "https://api.github.com"


# === Проверки перед пушем ===
def run_pre_commit():
    """Запускает pre-commit hooks перед созданием репозитория."""
    print("🧹 Запуск pre-commit проверок...")
    result = subprocess.run(
        ["pre-commit", "run", "--all-files"],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print("❌ Pre-commit проверки не пройдены. Исправь ошибки и повтори попытку.")
        sys.exit(1)
    print("✅ Все pre-commit проверки пройдены!\n")


def run_tests():
    """Запускает pytest и останавливает скрипт, если тесты не прошли."""
    print("🧪 Запуск тестов перед созданием репозитория...")
    result = subprocess.run(["pytest", "-q"], capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print("❌ Тесты не прошли, репозиторий не будет создан.")
        sys.exit(1)
    print("✅ Все тесты прошли успешно!\n")


# === Работа с GitHub API ===
def create_repo(repo_name, private=False):
    """Создаёт новый репозиторий на GitHub."""
    headers = {"Authorization": f"token {TOKEN}"}
    data = {"name": repo_name, "private": private, "auto_init": True}
    resp = requests.post(f"{API_URL}/user/repos", headers=headers, json=data)

    if resp.status_code == 201:
        print(f"✅ Репозиторий {repo_name} успешно создан.")
        return resp.json()["full_name"]
    else:
        print(f"❌ Ошибка при создании репозитория: {resp.text}")
        return None


def upload_file(repo, local_path, repo_path, message):
    """Загружает один файл в репозиторий."""
    headers = {"Authorization": f"token {TOKEN}"}
    with open(local_path, "rb") as f:
        content = base64.b64encode(f.read()).decode("utf-8")

    url = f"{API_URL}/repos/{repo}/contents/{repo_path}"
    data = {"message": message, "content": content, "branch": "main"}
    resp = requests.put(url, headers=headers, json=data)

    if resp.status_code in (201, 200):
        print(f"📁 Файл {repo_path} успешно загружен.")
    else:
        print(f"⚠️ Ошибка при загрузке {repo_path}: {resp.text}")


# === Фильтрация ненужных файлов ===
EXCLUDE_PATTERNS = (
    ".benchmarks/",
    ".mypy_cache",
    ".pytest_cache",
    "__pycache__",
    ".venv",
    ".idea",
    ".vscode",
    ".git/",
    "coverage.json",
    "screenshot.png"
)

def should_upload(path: str) -> bool:
    """Возвращает False, если путь содержит нежелательные файлы или папки."""
    return not any(ex in path for ex in EXCLUDE_PATTERNS)


def upload_project(repo_name, local_folder):
    """Загружает все файлы проекта в новый репозиторий, кроме мусора."""
    repo_fullname = f"{USERNAME}/{repo_name}"

    for root, dirs, files in os.walk(local_folder):
        # Исключаем ненужные директории
        dirs[:] = [d for d in dirs if should_upload(d)]

        for file in files:
            local_path = os.path.join(root, file)
            relative_path = os.path.relpath(local_path, local_folder)

            # Пропускаем ненужные файлы
            if not should_upload(relative_path) or file.endswith(".pyc") or file == ".env" or file == ".coverage":
                print(f"⛔ Пропущен файл: {relative_path}")
                continue

            upload_file(repo_fullname, local_path, relative_path, f"Add {relative_path}")

    print("✅ Все файлы загружены!")


def encrypt_secret(public_key: str, secret_value: str) -> str:
    """Шифрует секрет для отправки в GitHub API."""
    key = public.PublicKey(public_key.encode("utf-8"), encoding.Base64Encoder())
    sealed_box = public.SealedBox(key)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")


def create_secret(repo_full_name, secret_name, secret_value):
    """Создаёт secret в репозитории."""
    headers = {"Authorization": f"token {TOKEN}"}

    # 1️⃣ Получаем публичный ключ репозитория
    key_url = f"{API_URL}/repos/{repo_full_name}/actions/secrets/public-key"
    r = requests.get(key_url, headers=headers)
    if r.status_code != 200:
        print(f"❌ Не удалось получить ключ для {repo_full_name}: {r.text}")
        return
    key_data = r.json()
    print(f"🧩 Creating secret {secret_name}: {secret_value!r}")

    # 2️⃣ Шифруем секрет
    encrypted = encrypt_secret(key_data["key"], secret_value)

    # 3️⃣ Отправляем секрет
    put_url = f"{API_URL}/repos/{repo_full_name}/actions/secrets/{secret_name}"
    data = {"encrypted_value": encrypted, "key_id": key_data["key_id"]}
    resp = requests.put(put_url, headers=headers, json=data)

    if resp.status_code in (201, 204):
        print(f"🔐 Secret '{secret_name}' успешно добавлен в {repo_full_name}")
    else:
        print(f"⚠️ Ошибка при создании секрета '{secret_name}': {resp.text}")


# === Главный запуск ===
if __name__ == "__main__":
    repo_name = "flask-email-auto-3"
    local_folder = PROJECT_ROOT

    # 1️⃣ Запуск pre-commit и pytest
    run_pre_commit()
    run_tests()

    # 2️⃣ Создание репозитория и заливка файлов
    created = create_repo(repo_name)
    if created:
        upload_project(repo_name, local_folder)

        repo_fullname = f"{USERNAME}/{repo_name}"
        secrets_to_add = {
            "SMTP_SERVER": os.getenv("SMTP_SERVER"),
            "SMTP_PORT": os.getenv("SMTP_PORT"),
            "SENDER_EMAIL": os.getenv("SENDER_EMAIL"),
            "SENDER_PASSWORD": os.getenv("SENDER_PASSWORD"),
            "RECIPIENT_EMAIL": os.getenv("RECIPIENT_EMAIL")
        }

        for name, value in secrets_to_add.items():
            if value:
                create_secret(repo_fullname, name, value)
            else:
                print(f"⚠️ Пропущен секрет {name} — значение отсутствует")
    print("✅ Репозиторий полностью готов.\n")

    # 3️⃣ Генерация отчёта покрытия
    print("🧪 Запуск pytest с отчётом о покрытии...\n")
    result = subprocess.run(
        [
            "pytest",
            "--cov=app",
            "--cov-report=json",
            "--cov-report=term-missing",
            "--cov-fail-under=85"
        ],
        text=True,
        capture_output=True
    )
    print(result.stdout)

    if result.returncode == 0:
        print("✅ Покрытие успешно рассчитано и записано в coverage.json")
    else:
        print("❌ Ошибка при расчёте покрытия:")
        print(result.stderr)
        sys.exit(result.returncode)
