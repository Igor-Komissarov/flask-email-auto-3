import os
import requests
import pytest
from unittest.mock import patch
from nacl.public import PrivateKey
from nacl.encoding import Base64Encoder
from app.create_repo_and_push import (
    upload_project,
    upload_file,
    encrypt_secret,
    create_repo,
    create_secret
)
from unittest import mock

# === Fixtures ===
@pytest.fixture
def mock_requests_post(monkeypatch):
    """Мок для requests.post — имитирует успешное создание репозитория."""
    def mock_post(*args, **kwargs):
        class MockResponse:
            status_code = 201
            def json(self):
                return {"full_name": "mockuser/mockrepo"}
        return MockResponse()
    monkeypatch.setattr(requests, "post", mock_post)


@pytest.fixture
def mock_requests_put(monkeypatch):
    """Мок для requests.put — имитирует успешную загрузку файлов."""
    def mock_put(*args, **kwargs):
        class MockResponse:
            status_code = 201
            text = '{"ok": true}'
        return MockResponse()
    monkeypatch.setattr(requests, "put", mock_put)


# === Tests ===
def test_upload_project_performance(benchmark, mock_requests_put):
    """Performance: полная загрузка проекта (локальная логика)."""
    repo_name = "test-repo-benchmark"
    local_folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    benchmark(upload_project, repo_name, local_folder)


def test_upload_file_performance(benchmark, mock_requests_put):
    """Performance: измеряем скорость кодирования и загрузки одного файла."""
    repo = "mockuser/mockrepo"
    local_path = os.path.join(os.path.dirname(__file__), "test_performance.py")
    repo_path = "tests/test_performance.py"
    benchmark(upload_file, repo, local_path, repo_path, "Add test file")


def test_encrypt_secret_performance(benchmark):
    """Performance: скорость шифрования секретов."""
    from nacl.public import PrivateKey
    from nacl.encoding import Base64Encoder

    private_key = PrivateKey.generate()
    # кодируем публичный ключ в base64, как это делает GitHub API
    public_key = private_key.public_key.encode(encoder=Base64Encoder).decode("utf-8")
    super_value = "super_value"

    benchmark(encrypt_secret, public_key, super_value)



def test_create_repo_performance(benchmark, mock_requests_post):
    """Performance: измеряем время создания репозитория (мок)."""
    benchmark(create_repo, "test-repo-perf", private=True)


def test_create_secret_performance(benchmark):
    """Performance: измеряет скорость шифрования и отправки секрета."""
    # Генерируем корректный публичный ключ (32 байта)
    private_key = PrivateKey.generate()
    public_key_b64 = private_key.public_key.encode(encoder=Base64Encoder).decode("utf-8")

    with mock.patch("requests.get") as mock_get, mock.patch("requests.put") as mock_put:
        # Мокаем получение публичного ключа репозитория
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "key": public_key_b64,
            "key_id": "mock_key_id_123"
        }
        # Мокаем успешную отправку секрета
        mock_put.return_value.status_code = 201

        def run():
            create_secret("testuser/testrepo", "MY_SECRET", "super_value")

        benchmark(run)