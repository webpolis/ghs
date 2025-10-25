from github import Github, Auth
from typing import List, Dict, Any
import os
from tqdm import tqdm
import time


class GitHubStarsFetcher:
    def __init__(self, token: str):
        auth = Auth.Token(token)
        # Disable automatic retry to handle rate limits ourselves
        self.github = Github(auth=auth, retry=None, per_page=100)
        self.user = self._get_user_with_retry()
        # Cache username to avoid extra API calls
        self._username = None
        if self.user:
            try:
                self._username = self.user.login
            except:
                pass

    def _get_user_with_retry(self):
        """Get user with intelligent rate limit handling"""
        from github.GithubException import RateLimitExceededException

        max_retries = 3
        for attempt in range(max_retries):
            try:
                user = self.github.get_user()
                # Force load user data to trigger any rate limit errors now
                _ = user.login
                return user
            except RateLimitExceededException as e:
                # Rate limit exceeded - check when it resets
                try:
                    rate_limit = self.github.get_rate_limit()
                    core = rate_limit.core
                    wait_time = max((core.reset - time.time()) + 5, 0)

                    if wait_time > 0:
                        minutes = int(wait_time // 60)
                        seconds = int(wait_time % 60)
                        print(f"\n⚠️  GitHub API rate limit exceeded!")
                        print(f"    Resets in: {minutes}min {seconds}s")
                        print(f"    Waiting until {core.reset.strftime('%H:%M:%S')}...")
                        time.sleep(wait_time)

                    # After waiting, retry
                    if attempt < max_retries - 1:
                        continue
                except:
                    # Fallback if we can't get rate limit info
                    wait_time = 3600  # Wait 1 hour
                    print(f"\n⚠️  Rate limit exceeded. Waiting 1 hour...")
                    time.sleep(wait_time)

                if attempt == max_retries - 1:
                    raise
            except Exception as e:
                if attempt < max_retries - 1:
                    # Some other error, retry with exponential backoff
                    time.sleep(2 ** attempt)
                else:
                    raise

    def _check_rate_limit(self):
        """Check if we're approaching rate limit and wait if needed"""
        from github.GithubException import RateLimitExceededException

        try:
            rate_limit = self.github.get_rate_limit()
            core = rate_limit.core

            if core.remaining == 0:
                # Already rate limited
                wait_time = max((core.reset - time.time()) + 5, 0)
                if wait_time > 0:
                    minutes = int(wait_time // 60)
                    seconds = int(wait_time % 60)
                    print(f"\n⚠️  GitHub API rate limit exceeded!")
                    print(f"    Resets in: {minutes}min {seconds}s")
                    print(f"    Waiting until {core.reset.strftime('%H:%M:%S')}...")
                    time.sleep(wait_time)
            elif core.remaining < 100:  # If less than 100 requests remaining
                print(f"\n⚠️  Low on API quota: {core.remaining} requests remaining")
                print(f"    Resets in: {int((core.reset - time.time()) // 60)}min")
        except RateLimitExceededException:
            # Already rate limited, wait
            try:
                rate_limit = self.github.get_rate_limit()
                core = rate_limit.core
                wait_time = max((core.reset - time.time()) + 5, 0)
                if wait_time > 0:
                    minutes = int(wait_time // 60)
                    seconds = int(wait_time % 60)
                    print(f"\n⚠️  GitHub API rate limit exceeded!")
                    print(f"    Resets in: {minutes}min {seconds}s")
                    print(f"    Waiting until {core.reset.strftime('%H:%M:%S')}...")
                    time.sleep(wait_time)
            except:
                pass
        except:
            pass  # If we can't check rate limit, continue

    def get_starred_repositories(self) -> List[Dict[str, Any]]:
        self._check_rate_limit()
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
        if self._username:
            return self._username
        # Fallback if cache failed
        try:
            self._username = self.user.login
            return self._username
        except:
            return "unknown"

    def get_rate_limit_status(self) -> dict:
        """Get current rate limit status"""
        try:
            rate_limit = self.github.get_rate_limit()
            core = rate_limit.core
            return {
                "remaining": core.remaining,
                "limit": core.limit,
                "reset": core.reset,
                "reset_in_seconds": int((core.reset - time.time()))
            }
        except:
            return None

    def close(self):
        self.github.close()
