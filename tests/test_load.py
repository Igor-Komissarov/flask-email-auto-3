import concurrent.futures
import requests
from unittest import mock
from app.create_repo_and_push import upload_file, run_pre_commit, run_tests
import os
import time


def fake_put(*args, **kwargs):
    """Мок для имитации успешной загрузки."""
    class FakeResponse:
        status_code = 201
    return FakeResponse()


def test_upload_file_load():
    """Load test: имитирует 50 одновременных загрузок."""
    repo = "mockuser/mockrepo"
    local_path = os.path.join(os.path.dirname(__file__), "test_performance.py")
    repo_path = "tests/test_performance.py"

    with mock.patch("requests.put", side_effect=fake_put):
        start = time.perf_counter()

        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [
                executor.submit(upload_file, repo, local_path, f"{repo_path}_{i}.py", "Add test")
                for i in range(50)
            ]
            for f in concurrent.futures.as_completed(futures):
                f.result()

        duration = time.perf_counter() - start
        print(f"⏱ Load-test: 50 параллельных загрузок завершены за {duration:.3f} сек")
        assert duration < 2.0  # например, должно уложиться в 2 секунды

def test_upload_file_stress():
    """Stress test: находим предел устойчивости при массовой загрузке."""
    repo = "mockuser/mockrepo"
    local_path = os.path.join(os.path.dirname(__file__), "test_performance.py")
    repo_path = "tests/test_performance.py"

    with mock.patch("requests.put", side_effect=fake_put):
        for batch_size in [10, 50, 100, 200, 400, 800]:
            start = time.perf_counter()
            with concurrent.futures.ThreadPoolExecutor(max_workers=batch_size) as executor:
                futures = [
                    executor.submit(upload_file, repo, local_path, f"{repo_path}_{i}.py", "Add test")
                    for i in range(batch_size)
                ]
                for f in concurrent.futures.as_completed(futures):
                    f.result()
            duration = time.perf_counter() - start
            print(f"🔥 {batch_size} параллельных задач → {duration:.3f} сек")
            if duration > 5:
                print("⚠️ Система достигла предела производительности.")
                break

# def test_pre_commit_load():
#     """Load test: проверяем устойчивость pre-commit при множественных запусках."""
#     start = time.perf_counter()
#     with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
#         futures = [executor.submit(run_pre_commit) for _ in range(10)]
#         for f in concurrent.futures.as_completed(futures):
#             try:
#                 f.result()
#             except SystemExit:
#                 # pre-commit сам вызывает sys.exit(1) при ошибке — игнорируем
#                 pass
#     duration = time.perf_counter() - start
#     print(f"⚙️ Load test: 10 pre-commit checks выполнены за {duration:.2f} сек")


# def test_run_tests_stress():
#     """Stress test: многократные запуски pytest подряд."""
#     for n in [1, 3, 5, 10]:
#         start = time.perf_counter()
#         for _ in range(n):
#             try:
#                 run_tests()
#             except SystemExit:
#                 # pytest завершает процесс — это нормально
#                 pass
#         duration = time.perf_counter() - start
#         print(f"🔥 {n} последовательных запусков pytest → {duration:.2f} сек")
#         if duration > 15:
#             print("⚠️ Тестовая система достигла предела (pytest слишком медленный).")
#             break
