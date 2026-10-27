"""Build profile cards from public GitHub data. Standard library only; no private data."""
import collections
import datetime as dt
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request
from xml.sax.saxutils import escape

OWNER = "pengmoubuaixuexi"
ROOT = Path(__file__).resolve().parents[1]
API = "https://api.github.com"
COLORS = ["#38bdf8", "#818cf8", "#34d399", "#fbbf24", "#f472b6"]


def get(path):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "Tao-Peng-public-profile"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    for attempt in range(3):
        try:
            request = urllib.request.Request(API + path, headers=headers)
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code < 500 or attempt == 2:
                raise
        except (urllib.error.URLError, TimeoutError, OSError):
            if attempt == 2:
                raise
        time.sleep(2 ** attempt)


def fetch():
    repositories = []
    page = 1
    while True:
        batch = get(f"/users/{OWNER}/repos?type=owner&per_page=100&page={page}")
        repositories.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    own = [r for r in repositories if not r["private"] and not r["fork"]
           and r["owner"]["login"].lower() == OWNER and r["name"].lower() != OWNER]
    languages = collections.Counter()
    projects = []
    for repo in sorted(own, key=lambda r: r["name"].lower()):
        code = get(f'/repos/{OWNER}/{repo["name"]}/languages')
        languages.update(code)
        projects.append({"name": repo["name"], "stars": repo["stargazers_count"],
                         "forks": repo["forks_count"], "languageBytes": code})
    user = get(f"/users/{OWNER}")
    return {
        "owner": OWNER,
        "updatedAt": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scope": "Public owner repositories; forks and this profile repository excluded",
        "repositories": len(own), "stars": sum(r["stargazers_count"] for r in own),
        "forks": sum(r["forks_count"] for r in own), "followers": user["followers"],
        "languages": dict(languages.most_common()), "projects": projects,
    }


def text(x, y, value, size=14, color="#cbd5e1", weight=400):
    return (f'<text x="{x}" y="{y}" font-family="Segoe UI,Arial,sans-serif" '
            f'font-size="{size}" fill="{color}" font-weight="{weight}">{escape(str(value))}</text>')


def card(title, description, date, content):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="540" height="250" viewBox="0 0 540 250" '
            f'role="img" aria-label="{escape(title)}"><title>{escape(title)}</title>'
            f'<desc>{escape(description)}</desc><rect x="1" y="1" width="538" height="248" '
            'rx="14" fill="#0b1426" stroke="#20334e"/>'
            '<path d="M25 67H515" stroke="#20334e"/>'
            + text(25, 41, title, 21, "#7dd3fc", 650) + content
            + text(25, 227, f"Public data · Updated {date} UTC", 12, "#94a3b8") + '</svg>\n')


def render(data):
    date = data["updatedAt"][:10]
    rows = [("Public source repos", data["repositories"]), ("Stars earned", data["stars"]),
            ("Forks received", data["forks"]), ("Followers", data["followers"])]
    body = "".join(text(26, 96 + i * 30, label, 14) +
                   text(436, 96 + i * 30, f"{value:,}", 19, "#f8fafc", 650)
                   for i, (label, value) in enumerate(rows))
    stats = card("GitHub Stats", data["scope"], date, body)
    pairs = list(data["languages"].items())
    parts = pairs[:4]
    if len(pairs) > 4:
        parts.append(("Other", sum(value for _, value in pairs[4:])))
    total = sum(value for _, value in parts)
    body = text(25, 94, "Published code · proportion of language bytes", 13, "#94a3b8")
    if total:
        x = 25
        body += '<defs><clipPath id="bar"><rect x="25" y="112" width="490" height="16" rx="8"/></clipPath></defs><g clip-path="url(#bar)">'
        for i, (_, value) in enumerate(parts):
            width = 490 * value / total
            body += f'<rect x="{x:.3f}" y="112" width="{width:.3f}" height="16" fill="{COLORS[i]}"/>'
            x += width
        body += '</g>'
        for i, (language, value) in enumerate(parts):
            x, y = 25 + (i % 3) * 165, 157 + (i // 3) * 30
            body += f'<circle cx="{x + 4}" cy="{y - 5}" r="4" fill="{COLORS[i]}"/>'
            body += text(x + 15, y, f"{language} {value / total:.1%}", 12)
    else:
        body += text(25, 139, "No published language data yet.")
    languages = card("Languages", "Public repository language bytes; not a proficiency ranking", date, body)
    return stats, languages


def main():
    data = fetch()  # Fetch everything before changing a card; keep previous output on API errors.
    stats, languages = render(data)
    target = ROOT / "assets"
    target.mkdir(exist_ok=True)
    files = {"github-stats.svg": stats, "languages.svg": languages,
             "public-data.json": json.dumps(data, ensure_ascii=False, indent=2) + "\n"}
    for name, contents in files.items():
        (target / (name + ".tmp")).write_text(contents, encoding="utf-8")
    for name in files:
        (target / (name + ".tmp")).replace(target / name)
    print(f'Updated {data["repositories"]} public source repos, {data["stars"]} stars; {data["updatedAt"]}')


if __name__ == "__main__":
    main()
