"""White Rabbit (self-hosted GitLab/Redmine) API client.

No token/API-key auth — Django session cookie + CSRF. The bot logs in as a real
user (a dedicated bot account) and reuses the session cookie. Writes need
X-CSRFToken + an Origin header. The account must be is_staff or a project member,
else reads return empty / 404.
"""
import requests


class WhiteRabbit:
    def __init__(self, base_url: str, username: str, password: str,
                 origin: str | None = None):
        self.base = base_url.rstrip("/")
        self.username = username
        self.password = password
        # Origin must match CSRF_TRUSTED_ORIGINS (the site root, no /api).
        self.origin = origin or self.base.rsplit("/api", 1)[0]
        self.s = requests.Session()
        self._logged_in = False

    def _csrf(self) -> str:
        return self.s.cookies.get("csrftoken", "")

    def login(self, timeout: float = 20.0) -> None:
        self.s.get(f"{self.base}/auth/csrf/", timeout=timeout).raise_for_status()
        r = self.s.post(
            f"{self.base}/auth/login/",
            json={"username": self.username, "password": self.password},
            headers={"X-CSRFToken": self._csrf(), "Origin": self.origin},
            timeout=timeout,
        )
        r.raise_for_status()
        self._logged_in = True

    def _get(self, path: str, params: dict | None = None, timeout: float = 20.0):
        if not self._logged_in:
            self.login()
        url = f"{self.base}{path}"
        r = self.s.get(url, params=params, timeout=timeout)
        if r.status_code in (401, 403):
            self.login()
            r = self.s.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, payload: dict, timeout: float = 20.0):
        if not self._logged_in:
            self.login()
        url = f"{self.base}{path}"

        def do():
            return self.s.post(
                url, json=payload,
                headers={"X-CSRFToken": self._csrf(), "Origin": self.origin},
                timeout=timeout,
            )

        r = do()
        if r.status_code in (401, 403):
            self.login()
            r = do()
        r.raise_for_status()
        return r.json()

    def list_projects(self) -> list:
        d = self._get("/projects/")
        return d.get("results", d) if isinstance(d, dict) else d

    def list_issues(self, project: str | None = None, extra: dict | None = None) -> list:
        params = {}
        if project:
            params["project"] = project
        if extra:
            params.update(extra)
        d = self._get("/issues/", params=params or None)
        return d.get("results", d) if isinstance(d, dict) else d

    def create_issue(self, slug: str, title: str, **fields) -> dict:
        return self._post(f"/projects/{slug}/issues/", {"title": title, **fields})
