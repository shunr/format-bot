import subprocess


def format_python(repo_dir):
    subprocess.call(["black", repo_dir])
    subprocess.call(["isort", "-rc", "--verbose", repo_dir])
