from __future__ import annotations

import html
import base64
import json
import os
import re
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "dist"
OUT.mkdir(exist_ok=True)
ORIGIN = os.environ.get("SITE_ORIGIN", "https://forja-pixel.easypeony8.chatgpt.site").rstrip("/")

def load_projects() -> list[dict]:
    projects = []
    required = {"slug", "title", "kind", "tag", "version", "intro", "description", "compat", "category", "features", "steps", "note", "download", "download_label", "repo"}
    for file in sorted((ROOT / "projetos").glob("*.json")):
        project = json.loads(file.read_text(encoding="utf-8"))
        missing = required - project.keys()
        if missing:
            raise ValueError(f"{file.name}: faltam campos: {', '.join(sorted(missing))}")
        if file.stem != project["slug"] or not project["slug"].replace("-", "").isalnum():
            raise ValueError(f"{file.name}: slug inválido ou diferente do nome do arquivo")
        if project["category"] not in {"traducoes", "mods", "correcoes", "scripts"}:
            raise ValueError(f"{file.name}: categoria inválida")
        if not isinstance(project["features"], list) or not isinstance(project["steps"], list):
            raise ValueError(f"{file.name}: features e steps devem ser listas")
        project.setdefault("name", project["title"])
        project.setdefault("art", "script")
        project.setdefault("gallery", [])
        projects.append(project)
    if not projects:
        raise ValueError("Nenhum arquivo encontrado em projetos/*.json")
    return projects

TOPIC_CATEGORIES = {
    "forja-traducao": ("traducoes", "Tradução"),
    "forja-mod": ("mods", "Mod"),
    "forja-correcao": ("correcoes", "Correção"),
    "forja-script": ("scripts", "Script"),
}

NAME_PATTERNS = (
    (r"\b(?:traducao|traducoes|localizac\w*|pt\s*br|portugues)\b", ("traducoes", "Tradução")),
    (r"\b(?:correc\w*|corrig\w*|fix|patch|bugfix)\b", ("correcoes", "Correção")),
    (r"\b(?:userscript|scripts?|automac\w*|tampermonkey|greasemonkey)\b", ("scripts", "Script")),
    (r"\b(?:mods?|modificac\w*|add\s*on)\b", ("mods", "Mod")),
)

def infer_category(repo: dict) -> tuple[str, str]:
    # O nome tem prioridade: "correcao-jogo-ptbr" é uma correção, por exemplo.
    for source in (repo["name"], repo.get("description") or ""):
        plain = unicodedata.normalize("NFKD", source.lower())
        plain = "".join(char for char in plain if not unicodedata.combining(char))
        plain = re.sub(r"[._-]+", " ", plain)
        matches = [(match.start(), category) for pattern, category in NAME_PATTERNS
                   if (match := re.search(pattern, plain))]
        if matches:
            return min(matches, key=lambda item: item[0])[1]
    return ("outros", "Projeto")

def readme_summary(repo: dict, headers: dict) -> tuple[str, str, str]:
    """Lê o título e a apresentação do README em português, quando disponíveis."""
    url = f"https://api.github.com/repos/adestrador/{repo['name']}/readme"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=25) as response:
            payload = json.load(response)
        markdown = base64.b64decode(payload["content"]).decode("utf-8")
    except (urllib.error.URLError, KeyError, ValueError, UnicodeError) as error:
        print(f"README indisponível para {repo['name']}: {error}")
        return "", "", ""
    heading = ""
    for line in markdown.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("# ") and not heading:
            heading = re.sub(r"[*_`]", "", line[2:]).strip()
            continue
        if (line.startswith(("#", "!", "[", "<", "|", "-", ">", "```")) or
            re.match(r"^\*\*(?:Português|English)\b", line, re.I)):
            continue
        summary = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", line)
        summary = re.sub(r"[*_`]", "", summary).strip()
        if len(summary) >= 30:
            return heading, summary, markdown[:1800]
    return heading, "", markdown[:1800]

def automatic_title(repo: dict, kind: str, heading: str, summary: str) -> str:
    readable = re.sub(r"[._-]+", " ", repo["name"]).strip()
    readable = re.sub(r"\s+pt[ -]?br\b", "", readable, flags=re.I).strip()
    description = (repo.get("description") or "").strip()
    # A descrição ou a frase de apresentação do README descrevem o projeto
    # melhor do que o identificador técnico usado na URL do GitHub.
    candidate = description or summary
    if candidate and len(candidate) <= 140:
        return candidate.rstrip(". ")
    if heading and heading.casefold() != readable.casefold():
        return heading
    return f"Tradução PT-BR de {readable}" if kind == "Tradução" else readable if kind == "Projeto" else f"{kind}: {readable}"

def sync_github_projects(curated: list[dict]) -> list[dict]:
    if os.environ.get("SYNC_GITHUB_REPOS") != "1":
        return []
    curated_by_repo = {p["repo"].rstrip("/").split("/")[-1].lower(): p for p in curated}
    known = set(curated_by_repo)
    token = os.environ.get("GITHUB_TOKEN", "")
    projects = []
    for page in range(1, 12):
        url = f"https://api.github.com/users/adestrador/repos?type=owner&sort=created&direction=desc&per_page=100&page={page}"
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "Forja-Pixel-Sync", "X-GitHub-Api-Version": "2022-11-28"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=25) as response:
            repos = json.load(response)
        if not isinstance(repos, list):
            raise ValueError("Resposta inesperada da API do GitHub")
        for repo in repos:
            name = repo["name"]
            if repo["owner"]["login"].lower() == "adestrador" and name.lower() in curated_by_repo:
                curated_by_repo[name.lower()]["created_at"] = repo["created_at"]
            if (repo["owner"]["login"].lower() != "adestrador" or repo.get("fork") or
                repo.get("archived") or repo.get("disabled") or repo.get("private") or
                name.lower() == "forja-pixel" or name.lower() in known):
                continue
            known.add(name.lower())
            heading, summary, readme_intro = readme_summary(repo, headers)
            selected_topic = next((TOPIC_CATEGORIES[t] for t in (repo.get("topics") or []) if t in TOPIC_CATEGORIES), None)
            category, kind = selected_topic or infer_category({**repo, "description": (repo.get("description") or "") + " " + readme_intro})
            readable = re.sub(r"[._-]+", " ", name).strip()
            readable = re.sub(r"\s+pt[ -]?br\b", "", readable, flags=re.I).strip()
            title = automatic_title(repo, kind, heading, summary)
            projects.append({"slug": "github-" + name.lower(), "name": readable, "title": title,
                             "kind": kind, "category": category,
                             "intro": repo.get("description") or summary or "Projeto publicado no GitHub.",
                             "repo": repo["html_url"], "created_at": repo["created_at"], "automatic": True})
        if len(repos) < 100:
            break
    else:
        raise ValueError("Mais de 1.000 repositórios: aumente a paginação para evitar um catálogo incompleto")
    return projects

CURATED = load_projects()
AUTOMATIC = sync_github_projects(CURATED)
PROJECTS = sorted(CURATED + AUTOMATIC, key=lambda p: p.get("created_at", ""), reverse=True)
(OUT / "projetos.json").write_text(json.dumps(CURATED, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def e(value: str) -> str:
    return html.escape(value, quote=True)

def shell(title: str, description: str, content: str, prefix: str, canonical: str, image: str = "assets/forja-hero.webp") -> str:
    nav = f'''<header class="site-header"><div class="container nav-wrap"><a class="brand" href="{prefix}" aria-label="Forja Pixel — início"><span class="brand-icon" aria-hidden="true"><i></i><i></i><i></i><i></i></span><span>FORJA<span class="brand-accent">PIXEL</span></span></a><nav aria-label="Navegação principal"><a href="{prefix}#projetos">Projetos</a><a href="{prefix}#sobre">Sobre</a><a class="nav-github" href="https://github.com/adestrador" target="_blank" rel="noopener noreferrer">GitHub <span aria-hidden="true">↗</span></a></nav></div></header>'''
    return f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#0b121a"><title>{e(title)}</title><meta name="description" content="{e(description)}"><link rel="canonical" href="{e(canonical)}"><meta property="og:type" content="website"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(description)}"><meta property="og:image" content="{e(ORIGIN + '/' + image)}"><meta property="og:url" content="{e(canonical)}"><link rel="icon" type="image/svg+xml" href="{prefix}assets/favicon.svg"><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet"><link rel="stylesheet" href="{prefix}assets/site.css"></head><body>{nav}{content}<footer class="site-footer"><div class="container footer-wrap"><span class="brand mini">FORJA<span class="brand-accent">PIXEL</span></span><p>Criações independentes para jogos e internet.</p><a href="https://github.com/adestrador" target="_blank" rel="noopener noreferrer">Repositórios no GitHub ↗</a></div></footer><script src="{prefix}assets/site.js" defer></script></body></html>'''

def card(p: dict) -> str:
    terms = (p['title'] + ' ' + p['name'] + ' ' + p['kind'] + ' ' + p['intro']).lower()
    version = '' if p.get('automatic') else f'<span>v{e(p["version"])}</span>'
    return f'''<article class="project-card" data-repo="{e(p['repo'].rstrip('/').split('/')[-1].lower())}" data-category="{p['category']}" data-search="{e(terms)}"><div class="card-body"><div class="card-meta"><span>{e(p['kind'])}</span>{version}</div><h3><a href="projetos/{e(p['slug'])}/">{e(p['title'])}</a></h3><p>{e(p['intro'])}</p><a class="text-link" href="projetos/{e(p['slug'])}/">Ver projeto <span aria-hidden="true">↗</span></a></div></article>'''

home_content = f'''<main><section class="hero"><div class="hero-image" aria-hidden="true"></div><div class="container hero-inner"><div class="hero-copy"><span class="eyebrow"><span class="eyebrow-line"></span> TRADUÇÕES · MODS · CORREÇÕES · SCRIPTS</span><h1>Forja Pixel</h1><p>Projetos independentes para jogos de PC e páginas da internet.</p><a class="hero-project-link" href="#projetos">Ver projetos <span aria-hidden="true">↓</span></a></div></div></section><section class="work-section" id="projetos"><div class="container"><div class="section-heading"><div><h2>Projetos</h2></div></div><div class="catalog-tools"><div class="filters" role="group" aria-label="Filtrar projetos"><button class="filter is-active" type="button" data-filter="todos" aria-pressed="true">Todos</button><button class="filter" type="button" data-filter="traducoes" aria-pressed="false">Traduções</button><button class="filter" type="button" data-filter="mods" aria-pressed="false">Mods</button><button class="filter" type="button" data-filter="correcoes" aria-pressed="false">Correções</button><button class="filter" type="button" data-filter="scripts" aria-pressed="false">Scripts</button></div><label class="search-box"><span class="sr-only">Buscar projetos</span><svg aria-hidden="true" viewBox="0 0 24 24" fill="none"><circle cx="11" cy="11" r="6.5" stroke="currentColor" stroke-width="1.7"/><path d="m16 16 4.5 4.5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg><input id="project-search" type="search" placeholder="Buscar projeto..." autocomplete="off"></label></div><div class="project-grid">{''.join(card(p) for p in PROJECTS)}</div><p class="no-results" id="no-results" hidden>Nenhum projeto encontrado para essa busca.</p></div></section><section class="about-section" id="sobre"><div class="container about-grid"><div><span class="section-kicker">SOBRE</span><h2>Forja Pixel</h2></div><div><p>Reúne traduções, mods, correções e scripts publicados em código aberto. As fichas detalhadas trazem compatibilidade, instalação e ligação para o projeto no GitHub.</p></div></div></section></main>'''

home_content = home_content.replace('</div><label class="search-box">', '<button class="filter" type="button" data-filter="outros" aria-pressed="false">Outros</button></div><label class="search-box">')
home = shell("Forja Pixel — Traduções, correções e scripts originais", "Projetos independentes para jogos de PC e internet: traduções em português, correções e scripts com páginas individuais e instruções claras.", home_content, "./", ORIGIN + "/")
home = home.replace('</head>', '<script type="application/ld+json">'+json.dumps({"@context":"https://schema.org","@type":"WebSite","name":"Forja Pixel","url":ORIGIN+"/"},ensure_ascii=False)+'</script></head>')
(OUT / "index.html").write_text(home, encoding="utf-8")

# Evita manter páginas antigas quando um projeto for removido ou renomeado.
import shutil
shutil.rmtree(OUT / "projetos", ignore_errors=True)

for p in PROJECTS:
    if p.get("automatic"):
        main = f'''<main><div class="detail-hero"><div class="detail-backdrop script"></div><div class="container detail-hero-inner"><a class="breadcrumb" href="../../">← Todos os projetos</a><div class="detail-heading"><span class="eyebrow"><span class="eyebrow-line"></span>{e(p['kind']).upper()} · GITHUB</span><h1>{e(p['title'])}</h1><p>{e(p['intro'])}</p><div class="detail-actions"><a class="button button-primary" href="{e(p['repo'])}" target="_blank" rel="noopener noreferrer">Ver projeto no GitHub ↗</a></div></div></div></div><div class="container detail-layout"><div class="detail-main"><section class="detail-section"><span class="section-kicker">O PROJETO</span><h2>Sobre</h2><p class="large-copy">{e(p['intro'])}</p><p>Consulte o repositório para arquivos, instruções e versões disponíveis.</p></section></div></div><div class="container more-work"><div class="more-work-line"></div><a href="../../#projetos">← Voltar à vitrine de projetos</a></div></main>'''
        path = OUT / "projetos" / p["slug"] / "index.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(shell(f"{p['title']} | Forja Pixel", p['intro'], main, "../../", ORIGIN+f"/projetos/{p['slug']}/"), encoding="utf-8")
        continue
    art = ''
    gallery = '' if not p['gallery'] else f'''<section class="detail-section gallery-section"><div class="section-heading"><div><span class="section-kicker">NA PRÁTICA</span><h2>Capturas do projeto</h2></div></div><div class="gallery">{''.join(f'<a href="../../assets/{img}" target="_blank" rel="noopener noreferrer"><img src="../../assets/{img}" alt="Captura {i+1} de {e(p["name"])}" loading="lazy"></a>' for i,img in enumerate(p['gallery']))}</div></section>'''
    main = f'''<main><div class="detail-hero"><div class="detail-backdrop {p['art']}">{art}</div><div class="container detail-hero-inner"><a class="breadcrumb" href="../../">← Todos os projetos</a><div class="detail-heading"><span class="eyebrow"><span class="eyebrow-line"></span>{e(p['kind']).upper()} · {e(p['tag']).upper()}</span><h1>{e(p['title'])}</h1><p>{e(p['intro'])}</p><div class="detail-actions"><a class="button button-primary" href="{e(p['download'])}" target="_blank" rel="noopener noreferrer">{e(p['download_label'])} <span aria-hidden="true">↗</span></a><a class="button button-outline" href="{e(p['repo'])}" target="_blank" rel="noopener noreferrer">Ver repositório</a></div></div></div></div><div class="container detail-layout"><div class="detail-main"><section class="detail-section"><span class="section-kicker">O PROJETO</span><h2>O que foi criado</h2><p class="large-copy">{e(p['description'])}</p><ul class="feature-list">{''.join('<li>'+e(x)+'</li>' for x in p['features'])}</ul></section>{gallery}<section class="detail-section"><span class="section-kicker">PASSO A PASSO</span><h2>Como instalar</h2><ol class="step-list">{''.join('<li><span>'+str(i+1).zfill(2)+'</span><p>'+e(x)+'</p></li>' for i,x in enumerate(p['steps']))}</ol></section></div><aside class="detail-aside"><div class="info-panel"><h2>Ficha do projeto</h2><dl><div><dt>Tipo</dt><dd>{e(p['kind'])}</dd></div><div><dt>Versão</dt><dd>{e(p['version'])}</dd></div><div><dt>Compatibilidade</dt><dd>{e(p['compat'])}</dd></div><div><dt>Distribuição</dt><dd>Gratuita · GitHub</dd></div></dl><a class="button button-primary button-full" href="{e(p['download'])}" target="_blank" rel="noopener noreferrer">{e(p['download_label'])} ↗</a></div><div class="aside-note"><strong>Antes de instalar</strong><p>{e(p['note'])}</p><a href="{e(p['repo'])}" target="_blank" rel="noopener noreferrer">Ver documentação completa ↗</a></div></aside></div><div class="container more-work"><div class="more-work-line"></div><a href="../../#projetos">← Voltar à vitrine de projetos</a></div></main>'''
    path=OUT / "projetos" / p['slug'] / "index.html"
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(shell(f"{p['title']} | Forja Pixel",p['intro'],main,"../../",ORIGIN+f"/projetos/{p['slug']}/"),encoding="utf-8")

urls=[ORIGIN+"/"]+[ORIGIN+f"/projetos/{p['slug']}/" for p in PROJECTS]
(OUT/"sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'  <url><loc>{e(u)}</loc></url>\n' for u in urls)+'</urlset>\n',encoding='utf-8')
(OUT/"robots.txt").write_text('User-agent: *\nAllow: /\nSitemap: '+ORIGIN+'/sitemap.xml\n',encoding='utf-8')
print(f"Built {len(PROJECTS)+1} pages for {ORIGIN}")
