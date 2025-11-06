import cProfile
import pstats
import io
from unittest.mock import patch
from app.create_repo_and_push import upload_project
import os
import requests


def fake_put(*args, **kwargs):
    """Мокаем requests.put, чтобы не лез в GitHub."""
    class FakeResponse:
        status_code = 200
        def json(self):
            return {"ok": True}
    return FakeResponse()


def profile_upload_project():
    repo_name = "profile-test-repo"
    local_folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    with patch.object(requests, "put", side_effect=fake_put):
        profiler = cProfile.Profile()
        profiler.enable()

        upload_project(repo_name, local_folder)

        profiler.disable()
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats("cumtime")
        ps.print_stats(20)
        print(s.getvalue())


if __name__ == "__main__":
    profile_upload_project()
