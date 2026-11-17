"""Gera os cards SVG do README: radar de linguagens, barras de linguagens e estatisticas.

Usa so a biblioteca padrao do Python (nao precisa instalar nada).

  python scripts/generate_cards.py          # dados reais (precisa de GH_TOKEN)
  python scripts/generate_cards.py --demo   # dados de exemplo, pra testar o visual

Variaveis de ambiente:
  GH_TOKEN       token da API do GitHub (no Actions ja vem pronto)
  GH_USER        seu usuario (padrao: Fe403)
  EXCLUDE_LANGS  linguagens a ignorar, separadas por virgula (ex: "Shell,Jupyter Notebook")
  CARDS_DIR      pasta de saida (padrao: assets/cards)
"""
import json
import math
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

USER = os.environ.get("GH_USER", "Fe403")
TOKEN = os.environ.get("GH_TOKEN", "")
OUT = Path(os.environ.get("CARDS_DIR", "assets/cards"))
EXCLUDE = {s.strip().lower() for s in os.environ.get("EXCLUDE_LANGS", "").split(",") if s.strip()}
TOP_N = 5

# Visual (tema escuro com destaque verde-agua)
BG, BORDER, ACCENT = "#0a0e14", "#e6edf3", "#19e6b0"
TEXT, MUTED, GRID, TRACK = "#c9d1d9", "#8b949e", "#30363d", "#21262d"
FONT = "'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif"

QUERY = """
query($login: String!) {
  user(login: $login) {
    pullRequests { totalCount }
    contributionsCollection { totalCommitContributions }
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""


def fetch_data():
    if not TOKEN:
        raise SystemExit("Defina GH_TOKEN (no GitHub Actions ele ja existe).")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "profile-cards",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    if "errors" in payload:
        raise SystemExit(f"Erro da API do GitHub: {payload['errors']}")
    user = payload["data"]["user"]

    sizes, stars = {}, 0
    for repo in user["repositories"]["nodes"]:
        stars += repo["stargazerCount"]
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            if name.lower() in EXCLUDE:
                continue
            size, color = sizes.get(name, (0, edge["node"]["color"] or MUTED))
            sizes[name] = (size + edge["size"], color)

    total = sum(s for s, _ in sizes.values()) or 1
    langs = sorted(
        ((n, c, s / total * 100) for n, (s, c) in sizes.items()),
        key=lambda t: t[2],
        reverse=True,
    )
    return {
        "langs": langs,
        "repos": user["repositories"]["totalCount"],
        "commits": user["contributionsCollection"]["totalCommitContributions"],
        "prs": user["pullRequests"]["totalCount"],
        "stars": stars,
    }


def demo_data():
    return {
        "langs": [
            ("HTML", "#e34c26", 48.0),
            ("TypeScript", "#3178c6", 27.0),
            ("Python", "#3572A5", 19.0),
            ("CSS", "#563d7c", 7.2),
        ],
        "repos": 4, "commits": 5, "prs": 1, "stars": 0,
    }


# ---------- helpers ----------
def lighten(color, amount=0.3):
    """Clareia a cor da linguagem pra ela aparecer bem no fundo escuro."""
    if not (isinstance(color, str) and len(color) == 7 and color.startswith("#")):
        return MUTED
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    r, g, b = (round(c + (255 - c) * amount) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


PALETTE = {  # cores vivas pras linguagens mais comuns (as demais usam a cor do GitHub, clareada)
    "HTML": "#ef4444", "TypeScript": "#a855f7", "Python": "#3b82f6", "CSS": "#ec4899",
    "JavaScript": "#facc15", "Java": "#f97316", "C": "#94a3b8", "C++": "#f472b6",
    "C#": "#22c55e", "Dart": "#06b6d4", "Shell": "#4ade80", "PHP": "#818cf8", "Kotlin": "#c084fc",
}


def color_for(name, github_color):
    return PALETTE.get(name) or lighten(github_color, 0.2)


def fmt_pct(p):
    s = f"{p:.1f}"
    return (s[:-2] if s.endswith(".0") else s) + "%"


def head(w, h, title=None):
    s = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
         f'viewBox="0 0 {w} {h}" font-family="{FONT}">')
    s += (f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="10" fill="{BG}" '
          f'stroke="{BORDER}" stroke-opacity="0.85" stroke-width="1.5"/>')
    if title:
        s += f'<text x="20" y="34" fill="{ACCENT}" font-size="15" font-weight="600">{escape(title)}</text>'
    return s


def today_br():
    return datetime.now(timezone(timedelta(hours=-3))).strftime("%Y-%m-%d")


# ---------- cards ----------
def radar_svg(langs):
    W, H = 480, 340
    cx, cy, R = 240, 172, 100
    top = langs[:TOP_N]
    n = len(top)
    s = head(W, H, "Radar de linguagens")
    s += "<title>Radar de linguagens</title>"

    if n < 3:
        s += (f'<text x="{W / 2}" y="{H / 2}" text-anchor="middle" fill="{MUTED}" '
              f'font-size="13">Poucos dados ainda (precisa de 3 linguagens)</text>')
    else:
        def pt(i, frac):
            a = -math.pi / 2 + i * 2 * math.pi / n
            return cx + R * frac * math.cos(a), cy + R * frac * math.sin(a)

        for ring in (0.25, 0.5, 0.75, 1.0):
            pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (pt(i, ring) for i in range(n)))
            s += f'<polygon points="{pts}" fill="none" stroke="{GRID}" stroke-width="1"/>'
        for i in range(n):
            x, y = pt(i, 1)
            s += f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="{GRID}" stroke-width="1"/>'

        scale_max = math.ceil(top[0][2] / 10) * 10  # escala raiz quadrada
        fracs = [math.sqrt(p / scale_max) for _, _, p in top]
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (pt(i, f) for i, f in enumerate(fracs)))
        s += (f'<polygon points="{pts}" fill="{ACCENT}" fill-opacity="0.25" '
              f'stroke="{ACCENT}" stroke-width="2" stroke-linejoin="round"/>')
        for i, f in enumerate(fracs):
            x, y = pt(i, f)
            s += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{ACCENT}"/>'

        for i, (name, _, _) in enumerate(top):
            a = -math.pi / 2 + i * 2 * math.pi / n
            c, sn = math.cos(a), math.sin(a)
            lx, ly = cx + (R + 16) * c, cy + (R + 16) * sn
            anchor = "middle" if abs(c) < 0.3 else ("start" if c > 0 else "end")
            dy = 4 if abs(sn) < 0.9 else (-2 if sn < 0 else 12)
            s += (f'<text x="{lx:.1f}" y="{ly + dy:.1f}" text-anchor="{anchor}" '
                  f'fill="{TEXT}" font-size="12">{escape(name)}</text>')

    s += (f'<text x="20" y="{H - 16}" fill="{MUTED}" font-size="11">'
          f'Proporção de código por linguagem, escala raiz quadrada</text>')
    return s + "</svg>"


def bars_svg(langs):
    W, H = 480, 340
    top = langs[:TOP_N]
    s = head(W, H, "Principais linguagens")
    s += "<title>Principais linguagens</title>"
    bar_w = 440

    if not top:
        s += (f'<text x="{W / 2}" y="{H / 2}" text-anchor="middle" fill="{MUTED}" '
              f'font-size="13">Sem dados de linguagens ainda</text>')
        return s + "</svg>"

    # barra empilhada no topo
    s += f'<clipPath id="r"><rect x="20" y="52" width="{bar_w}" height="8" rx="4"/></clipPath>'
    s += f'<g clip-path="url(#r)"><rect x="20" y="52" width="{bar_w}" height="8" fill="{TRACK}"/>'
    x = 20.0
    for name, color, p in top:
        w = bar_w * p / 100
        s += f'<rect x="{x:.1f}" y="52" width="{w:.1f}" height="8" fill="{color_for(name, color)}"/>'
        x += w
    s += "</g>"

    # uma linha por linguagem
    top_pct = top[0][2] or 1
    for i, (name, color, p) in enumerate(top):
        y = 92 + i * 42
        col = color_for(name, color)
        s += f'<circle cx="26" cy="{y - 4}" r="5" fill="{col}"/>'
        s += f'<text x="40" y="{y}" fill="{TEXT}" font-size="13">{escape(name)}</text>'
        s += (f'<text x="460" y="{y}" text-anchor="end" fill="{col}" font-size="13" '
              f'font-weight="600">{fmt_pct(p)}</text>')
        s += f'<rect x="20" y="{y + 10}" width="{bar_w}" height="4" rx="2" fill="{TRACK}"/>'
        s += (f'<rect x="20" y="{y + 10}" width="{bar_w * p / top_pct:.1f}" height="4" '
              f'rx="2" fill="{col}"/>')

    s += f'<text x="20" y="{H - 16}" fill="{MUTED}" font-size="11">atualizado em {today_br()}</text>'
    return s + "</svg>"


def stats_svg(d):
    W, H = 970, 110
    s = head(W, H)
    s += "<title>Repositórios, commits, pull requests e estrelas</title>"
    items = [
        ("Repositórios", d["repos"]),
        ("Commits no último ano", d["commits"]),
        ("Pull requests", d["prs"]),
        ("Estrelas recebidas", d["stars"]),
    ]
    col_w = W / 4
    for i, (label, value) in enumerate(items):
        x = i * col_w + 24
        if i:
            s += (f'<line x1="{i * col_w:.1f}" y1="22" x2="{i * col_w:.1f}" y2="{H - 22}" '
                  f'stroke="{GRID}" stroke-width="1"/>')
        s += f'<text x="{x:.1f}" y="42" fill="{TEXT}" font-size="13">{escape(label)}</text>'
        s += f'<text x="{x:.1f}" y="82" fill="{ACCENT}" font-size="30">{value}</text>'
    return s + "</svg>"


def main():
    data = demo_data() if "--demo" in sys.argv else fetch_data()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "languages-radar.svg").write_text(radar_svg(data["langs"]), encoding="utf-8")
    (OUT / "languages-bars.svg").write_text(bars_svg(data["langs"]), encoding="utf-8")
    (OUT / "stats.svg").write_text(stats_svg(data), encoding="utf-8")
    print(f"Cards gerados em {OUT}/")


if __name__ == "__main__":
    main()

