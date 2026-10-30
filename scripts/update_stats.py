"""Refresh the profile header card and merged-PR list from public GitHub data. Standard library only; no private data."""
import datetime as dt
import json
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from xml.sax.saxutils import escape

OWNER = "pengmoubuaixuexi"
FLAGSHIP = "TAgent"
LIVE_VERSION = "v2.2"  # Updated by hand when a new minor version goes live.
ROOT = Path(__file__).resolve().parents[1]
API = "https://api.github.com"
SANS = "Segoe UI,-apple-system,Helvetica,Arial,'Microsoft YaHei',sans-serif"
MONO = "ui-monospace,SFMono-Regular,Consolas,Menlo,monospace"
THEMES = {
    "light": dict(panel="#f6f8fa", line="#d8dee4", ink="#1f2328", muted="#59636e", faint="#818b98",
                  accent="#0b7a75", node="#ffffff"),
    "dark": dict(panel="#151b23", line="#2a313c", ink="#f0f6fc", muted="#9198a1", faint="#6e7681",
                 accent="#3cc6bd", node="#0d1117"),
}
PR_START, PR_END = "<!-- merged-prs:start -->", "<!-- merged-prs:end -->"


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
    flagship = get(f"/repos/{OWNER}/{FLAGSHIP}")
    query = urllib.parse.quote(f"author:{OWNER} type:pr is:merged -user:{OWNER}")
    found = get(f"/search/issues?q={query}&sort=created&order=desc&per_page=100")
    if found.get("incomplete_results"):
        raise RuntimeError("GitHub search returned incomplete results; keeping the previous output")
    prs = [{"repo": item["repository_url"].split("/repos/", 1)[1], "number": item["number"],
            "title": item["title"], "url": item["html_url"],
            "mergedAt": (item.get("pull_request") or {}).get("merged_at") or item["closed_at"]}
           for item in found["items"]]
    repo_stars = {repo: get(f"/repos/{repo}")["stargazers_count"] for repo in {pr["repo"] for pr in prs}}
    return {
        "owner": OWNER,
        "updatedAt": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "flagship": FLAGSHIP, "flagshipStars": flagship["stargazers_count"],
        "mergedPullRequests": found["total_count"],
        "scope": "Merged pull requests authored by the owner in repositories the owner does not own",
        "pullRequests": prs, "repoStars": repo_stars,
    }


def text(x, y, value, size, color, family=SANS, weight=400, extra=""):
    return (f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" font-weight="{weight}" '
            f'fill="{color}" {extra}>{escape(str(value))}</text>')


def hero(data, c):
    w, h, gx, gy = 880, 300, 560, 52

    def node(x, y, label, strong=False):
        stroke = c["accent"] if strong else c["line"]
        color = c["accent"] if strong else c["ink"]
        return (f'<rect x="{x}" y="{y}" width="76" height="30" rx="7" fill="{c["node"]}" stroke="{stroke}" stroke-width="1.2"/>'
                + text(x + 38, y + 19.5, label, 12.5, color, MONO, extra='text-anchor="middle"'))

    def edge(d, dashed=False):
        dash = ' stroke-dasharray="4 4"' if dashed else ""
        return f'<path d="{d}" fill="none" stroke="{c["faint"]}" stroke-width="1.2"{dash} marker-end="url(#a)"/>'

    graph = (node(gx, gy, "route") + node(gx + 108, gy, "plan") + node(gx + 216, gy, "tools")
             + node(gx + 216, gy + 92, "verify") + node(gx + 108, gy + 92, "answer", strong=True)
             + edge(f"M{gx + 77} {gy + 15}H{gx + 104}") + edge(f"M{gx + 185} {gy + 15}H{gx + 212}")
             + edge(f"M{gx + 254} {gy + 31}V{gy + 88}") + edge(f"M{gx + 215} {gy + 107}H{gx + 188}")
             + edge(f"M{gx + 226} {gy + 92}C{gx + 205} {gy + 66} {gx + 162} {gy + 70} {gx + 150} {gy + 35}", dashed=True)
             + text(gx + 112, gy + 66, "reflect", 11, c["faint"], MONO))
    stats = [(f'{data["flagshipStars"]:,}', f"stars on {FLAGSHIP}"),
             (f'{data["mergedPullRequests"]:,}', "merged upstream PRs"),
             ("CVPR 2026", "SRGCD paper"), (LIVE_VERSION, "live at tagentapp.cn")]
    row = ""
    col = (w - 80) / len(stats)
    for i, (big, small) in enumerate(stats):
        x = 40 + i * col
        if i:
            row += f'<path d="M{x - 14} 226V270" stroke="{c["line"]}"/>'
        row += text(x, 248, big, 22, c["ink"], weight=650) + text(x, 268, small, 12.5, c["muted"])
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" '
            f'aria-label="Tao Peng — AI agent engineering, Java backend, 3D vision">'
            f'<title>Tao Peng — AI agent engineering, Java backend, 3D vision</title>'
            f'<desc>Public GitHub data · updated {data["updatedAt"][:10]} UTC</desc>'
            f'<defs><marker id="a" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">'
            f'<path d="M1 1L7 4L1 7" fill="none" stroke="{c["faint"]}" stroke-width="1.2"/></marker></defs>'
            f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="12" fill="{c["panel"]}" stroke="{c["line"]}"/>'
            + text(40, 60, "AI AGENTS · JAVA BACKEND · 3D VISION", 12, c["accent"], MONO, extra='letter-spacing="1.6"')
            + text(38, 118, "Tao Peng", 46, c["ink"], weight=700, extra='letter-spacing="-1"')
            + text(250, 118, "彭涛", 26, c["faint"])
            + text(40, 156, "I build agent systems that hold up in production —", 16, c["muted"])
            + text(40, 179, "routing, tools, memory and evaluation loops.", 16, c["muted"])
            + graph + f'<path d="M40 206H{w - 40}" stroke="{c["line"]}"/>' + row + "</svg>\n")


def markdown_text(value):
    return re.sub(r"([\\`*_\[\]<>])", r"\\\1", value)


def pr_block(data):
    groups = {}
    for pr in sorted(data["pullRequests"], key=lambda p: p["mergedAt"], reverse=True):
        groups.setdefault(pr["repo"], []).append(pr)
    lines = []
    for repo in sorted(groups, key=lambda r: (-data["repoStars"][r], r)):
        lines += [f"**[{repo}](https://github.com/{repo})**", ""]
        lines += [f'- [#{pr["number"]}]({pr["url"]}) {markdown_text(pr["title"])}' for pr in groups[repo]]
        lines.append("")
    return "\n".join(lines).rstrip("\n")


def main():
    data = fetch()  # Fetch everything before changing a file; keep previous output on API errors.
    readme_path = ROOT / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    start, end = readme.index(PR_START) + len(PR_START), readme.index(PR_END)
    files = {ROOT / "assets" / f"hero-{name}.svg": hero(data, colors) for name, colors in THEMES.items()}
    files[ROOT / "assets" / "public-data.json"] = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    files[readme_path] = readme[:start] + "\n" + pr_block(data) + "\n" + readme[end:]
    for path, contents in files.items():
        path.with_name(path.name + ".tmp").write_text(contents, encoding="utf-8", newline="\n")
    for path in files:
        path.with_name(path.name + ".tmp").replace(path)
    print(f'{FLAGSHIP}: {data["flagshipStars"]} stars; {data["mergedPullRequests"]} merged upstream PRs; {data["updatedAt"]}')


if __name__ == "__main__":
    main()
