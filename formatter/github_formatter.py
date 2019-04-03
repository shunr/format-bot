import hashlib
import os
import time
from shutil import rmtree

import git
from github import Github

from .flavor_text import FlavorText
from .python import format_python

TMP_DIR = "/tmp"
BRANCH_SUFFIX = "-auto-formatted"
RETRY_DELAY_MS = 400


class GithubFormatter:
    def __init__(self, token):
        self._github = Github(token)
        self.user = self._github.get_user()
        self.token = token

    def format(self, repo_name, branch):

        new_branch = branch + BRANCH_SUFFIX
        original_repo = self._github.get_repo(repo_name)
        fork = self.user.create_fork(original_repo)

        repo_hash = hashlib.sha224(repo_name.encode("utf-8")).hexdigest() + "_" + branch
        repo_dir = os.path.join(TMP_DIR, repo_hash)

        cloned = False
        while not cloned:
            try:
                repo = git.Repo.clone_from(fork.clone_url, repo_dir, branch=branch)
                cloned = True
            except git.exc.GitCommandError as e:
                # Fork not finished
                if e.status != 128:
                    raise e
                time.sleep(RETRY_DELAY_MS / 1000)

        repo.config_writer().set_value("user", "name", str(self.user.name)).release()
        repo.config_writer().set_value("user", "email", str(self.user.email)).release()

        repo.git.checkout("-b", new_branch)
        try:
            repo.git.pull("origin", new_branch)
        except git.exc.GitCommandError as e:
            print("Branch exists!")

        # Format code
        format_python(repo_dir)

        repo.git.add(A=True)
        repo.index.commit(FlavorText.COMMIT_MESSAGE)
        repo.git.remote("rm", "origin")
        repo.git.remote(
            "add",
            "origin",
            fork.clone_url.replace(
                "https://github.com",
                "https://{}:{}@github.com".format(self.user.login, self.token),
            ),
        )
        repo.git.push("origin", new_branch)

        # Create PR
        pr_head = "{}:{}".format(self.user.login, new_branch)
        pulls = original_repo.get_pulls(base=branch, head=pr_head, state="open")

        pr_exists = pulls.totalCount > 0
        if pr_exists:
            print(
                "Open PR already exists for {}:{} : {}".format(
                    repo_name, branch, pulls[0]
                )
            )
        else:
            original_repo.create_pull(
                title=FlavorText.PR_TITLE,
                body=FlavorText.PR_BODY,
                base=branch,
                head=pr_head,
            )

        rmtree(repo_dir)
        print("Done!")
