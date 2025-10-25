from github import Github, Auth
from typing import List, Dict, Any
import os
from tqdm import tqdm


class GitHubStarsFetcher:
    def __init__(self, token: str):
        auth = Auth.Token(token)
        self.github = Github(auth=auth)
        self.user = self.github.get_user()

    def get_starred_repositories(self) -> List[Dict[str, Any]]:
        starred = self.user.get_starred()
        repos = []

        total_count = starred.totalCount
        with tqdm(total=total_count, desc="Fetching stars", unit="repo") as pbar:
            for repo in starred:
                repo_data = {
                    "id": repo.id,
                    "full_name": repo.full_name,
                    "name": repo.name,
                    "description": repo.description,
                    "url": repo.html_url,
                    "stars": repo.stargazers_count,
                    "language": repo.language,
                    "created_at": repo.created_at.isoformat() if repo.created_at else None,
                    "updated_at": repo.updated_at.isoformat() if repo.updated_at else None,
                    "default_branch": repo.default_branch,
                    "owner": repo.owner.login,
                }
                repos.append(repo_data)
                pbar.update(1)

        return repos

    def get_username(self) -> str:
        return self.user.login

    def close(self):
        self.github.close()
