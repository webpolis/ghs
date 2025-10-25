import requests
from typing import Optional, Tuple
import time
import threading


class ReadmeFetcher:
    # Class-level rate limit tracking
    _rate_limit_lock = threading.Lock()
    _rate_limit_reset_time = 0
    _rate_limited = False

    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3.raw"  # Get raw content directly
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def _check_rate_limit(self, response):
        """Check and handle rate limiting across all threads"""
        if response.status_code == 403:
            with self._rate_limit_lock:
                # Check if we're rate limited
                if "X-RateLimit-Remaining" in response.headers:
                    remaining = int(response.headers.get("X-RateLimit-Remaining", 0))
                    if remaining == 0:
                        reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
                        wait_time = max(reset_time - time.time(), 0) + 5
                        self._rate_limited = True
                        self._rate_limit_reset_time = time.time() + wait_time
                        print(f"\n⚠️  Rate limit hit! Waiting {int(wait_time)}s until reset...")
                        time.sleep(wait_time)
                        self._rate_limited = False
                        return True
        return False

    def _wait_if_rate_limited(self):
        """Wait if another thread detected rate limiting"""
        with self._rate_limit_lock:
            if self._rate_limited:
                wait_time = max(self._rate_limit_reset_time - time.time(), 0)
                if wait_time > 0:
                    time.sleep(wait_time)

    def fetch_readme(self, owner: str, repo: str) -> Tuple[Optional[str], Optional[str]]:
        """Fetch README using GitHub's dedicated README API endpoint"""
        self._wait_if_rate_limited()

        # Use GitHub's README API endpoint - much more efficient!
        url = f"https://api.github.com/repos/{owner}/{repo}/readme"

        try:
            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                # We get raw content directly with the Accept header
                content = response.text
                # Try to determine type from Content-Type header or assume markdown
                content_type = response.headers.get("Content-Type", "")
                if "text/plain" in content_type:
                    readme_type = "text"
                else:
                    readme_type = "markdown"  # Most READMEs are markdown

                return content, readme_type

            elif response.status_code == 404:
                # No README found
                return None, None

            elif self._check_rate_limit(response):
                # Rate limit handled, retry
                return self.fetch_readme(owner, repo)

            return None, None

        except requests.exceptions.RequestException:
            return None, None

    def parse_content(self, content: str, readme_type: str) -> str:
        if not content:
            return ""

        content = content.strip()

        if len(content) > 50000:
            content = content[:50000]

        return content
