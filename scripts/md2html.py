#!/usr/bin/env python3
"""Convert the Bengali markdown learning files to static HTML for GitHub Pages.

Usage: python3 scripts/md2html.py
Output:
  docs/index.html                  — hub listing every topic
  docs/<topic>/index.html          — per-topic index (card list of files)
  docs/<topic>/<sub>/<file>.html   — one .html per .md file
PDFs are linked to the raw GitHub URL so they download from the public repo.
"""
import html
import os
import pathlib
import re
import shutil
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ROOT / 'docs'
REPO_RAW = 'https://raw.githubusercontent.com/ahsanjust/tazkiyah/main'
ASSET_SRC = ROOT / 'assets' / 'style.css'
ASSET_DST = DOCS / 'assets' / 'style.css'

FONT = ('Noto Sans Bengali:400,600,700&display=swap')

NOTICE_MARK = '**গুরুত্বপূর্ণ নোটিশ'

# dir-name -> (brand short title, one-line tagline)
TOPICS = {
    '01-কিবর-ও-উজব': ('তাযকিয়াহ — অহংকার (কিবর) ও উজব',
                       'কিবর ও উজব বোঝার ও তা থেকে বাঁচার পূর্ণাঙ্গ সংকলন — কুরআনের আয়াত, সহীহ হাদিস ও সাহাবিদের ঘটনা।'),
    '02-সালাত': ('তাযকিয়াহ — সালাত (নামাজ)',
                 'সালাতের মর্যাদা, শর্তাবলী, ফরজ-ওয়াজিব-সুন্নত, সঠিক পদ্ধতি, মাসআলা ও মাযহাব-তুলনা — দলিলসহ পূর্ণাঙ্গ সংকলন।'),
    '03-দ্বিধা-ও-সন্দেহ': ('তাযকিয়াহ — দ্বিধা ও সন্দেহ',
                           'প্রচলিত দ্বিধাগুলোর দলিলভিত্তিক সমাধান — ছবি আঁকা, AI-ছবি ও অন্যান্য জিজ্ঞাসা, কুরআন, সহীহ হাদিস ও আলেমদের মতামতের আলোকে।'),
}

NOTICE_TEXT = ('**গুরুত্বপূর্ণ নোটিশ (Important Notice):** এই কন্টেন্টটি AI (কৃত্রিম বুদ্ধিমত্তা) দিয়ে প্রস্তুত ও সংকলিত। '
               'AI কঠোর সূত্র-মান নীতি মেনে শুধু নির্ভরযোগ্য উৎস থেকে তথ্য সংগ্রহ করেছে — কেবল সহীহ/হাসান হাদিস ও সহীহ সনদের '
               'আসার রাখা হয়েছে, দুর্বল সনদ বাদ দেওয়া হয়েছে। তবে এটি কোনো আলেম বা মুহাদ্দিস কর্তৃক যাচাইকৃত নয়।')


def esc(s):
    return html.escape(s, quote=False)


def inline(text):
    """Bold/italic/code + basic escaping for a paragraph of markdown."""
    text = esc(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', text)
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    return text


def convert(md_text):
    """Very small markdown -> HTML converter for this project's files."""
    lines = md_text.split('\n')
    out = []
    i = 0
    in_list = None
    in_table = False
    table = []

    def close_list():
        nonlocal in_list
        if in_list:
            out.append(f'</{in_list}>')
            in_list = None

    def flush_table():
        nonlocal in_table, table
        if in_table:
            rows = ['<table>']
            for ri, row in enumerate(table):
                tag = 'th' if ri == 0 else 'td'
                cells = ''.join(f'<{tag}>{inline(c)}</{tag}>' for c in row)
                rows.append(f'<tr>{cells}</tr>')
            rows.append('</table>')
            out.append('\n'.join(rows))
            table = []
            in_table = False

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # tables
        if stripped.startswith('|'):
            cells = [c for c in stripped.strip('|').split('|')]
            if all(re.match(r'^[-:\s]+$', c) for c in cells):
                i += 1
                continue
            if not in_table:
                flush_table()
                close_list()
                in_table = True
            table.append(cells)
            i += 1
            continue
        if in_table:
            flush_table()

        # blank
        if not stripped:
            close_list()
            i += 1
            continue

        # headings
        m = re.match(r'^(#{1,4})\s+(.*)$', stripped)
        if m:
            close_list()
            lvl = len(m.group(1))
            out.append(f'<h{lvl}>{inline(m.group(2))}</h{lvl}>')
            i += 1
            continue

        # horizontal rule
        if re.match(r'^---+$', stripped):
            close_list()
            out.append('<hr>')
            i += 1
            continue

        # blockquote
        if stripped == '>' or stripped.startswith('> '):
            close_list()
            qlines = []
            while i < len(lines) and (lines[i].strip() == '>' or lines[i].strip().startswith('> ')):
                content = lines[i].strip()
                content = content[1:].strip() if content.startswith('>') else content
                if content:
                    qlines.append(content)
                i += 1
            body = '<br>\n'.join(inline(q) for q in qlines)
            cls = 'notice' if any(NOTICE_MARK in q for q in qlines) else 'quote'
            out.append(f'<blockquote class="{cls}">\n{body}\n</blockquote>')
            continue

        # lists
        m_ol = re.match(r'^(\d+)\.\s+(.*)$', stripped)
        m_ul = re.match(r'^[-*]\s+(.*)$', stripped)
        if m_ol:
            if in_list != 'ol':
                close_list()
                out.append('<ol>')
                in_list = 'ol'
            out.append(f'<li>{inline(m_ol.group(2))}</li>')
            i += 1
            continue
        if m_ul:
            if in_list != 'ul':
                close_list()
                out.append('<ul>')
                in_list = 'ul'
            out.append(f'<li>{inline(m_ul.group(1))}</li>')
            i += 1
            continue

        # paragraph
        close_list()
        para = [inline(stripped)]
        i += 1
        while i < len(lines) and lines[i].strip() and not lines[i].startswith('#') \
                and not lines[i].strip().startswith('>') and not lines[i].strip().startswith('|') \
                and not re.match(r'^(\d+\.|[-*])\s+', lines[i].strip()) \
                and not re.match(r'^---+$', lines[i].strip()):
            para.append(inline(lines[i].strip()))
            i += 1
        out.append(f'<p>{'<br>'.join(para)}</p>')

    close_list()
    flush_table()
    return '\n'.join(out)


def raw_pdf_url(md_path):
    rel = md_path.relative_to(ROOT)
    url = REPO_RAW + '/' + urllib.parse.quote(str(rel), safe='/.-')
    return url


def page(title, body, back_href='index.html', pdf_url=None, css_href='assets/style.css',
         banner=False, tagline=''):
    pdf_link = f'<a class="btn" href="{pdf_url}">📥 PDF ডাউনলোড</a>' if pdf_url else ''
    if banner:
        head = f"""<section class="page-banner">
  <a class="back" href="{back_href}">← সূচীপত্রে ফিরুন</a>
  <h1>{esc(title)}</h1>
  {pdf_link}
</section>
<main class="wrap">
  <p class="intro-text">{esc(tagline)}</p>"""
    else:
        head = f"""<main class="wrap">
  <div class="page-head">
    <a class="back" href="{back_href}">← সূচীপত্রে ফিরুন</a>
    <h1>{esc(title)}</h1>
    {pdf_link}
  </div>"""
    return f"""<!DOCTYPE html>
<html lang="bn">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} — তাযকিয়াহ</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family={FONT}" rel="stylesheet">
<link rel="stylesheet" href="{css_href}">
</head>
<body>
<header class="site-head">
  <a class="brand" href="{back_href}">তাযকিয়াহ</a>
</header>
{head}
  <article class="content">
{body}
  </article>
</main>
<footer class="site-foot">
  <p>AI-সংকলিত, আলেম-যাচাইকৃত নয় · <a href="{back_href}">সূচীপত্র</a></p>
</footer>
</body>
</html>
"""


def h1_of(text, fallback):
    for line in text.split('\n'):
        if line.startswith('# '):
            return line[2:].strip()
    return fallback


def topic_md_files(topic_dir):
    """All content .md files of a topic, in reading order (flat topics)."""
    files = []
    quran = topic_dir / 'কুরআন'
    hadith = topic_dir / 'হাদিস'
    stories = topic_dir / 'সাহাবিদের-ঘটনা'
    if quran.is_dir():
        files += sorted(quran.glob('*.md'))
    if hadith.is_dir():
        files += sorted(hadith.glob('*.md'))
    files += sorted(p for p in topic_dir.glob('[0-9][0-9]-*.md')
                    if not p.name.startswith('00-'))
    if stories.is_dir():
        files += sorted(stories.glob('*.md'))
    return files


def unit_md_files(unit_dir):
    """Content .md files inside a confusion unit (nested topic), in reading order."""
    files = []
    for sub in ('কুরআন', 'হাদিস'):
        d = unit_dir / sub
        if d.is_dir():
            files += sorted(d.glob('*.md'))
    files += sorted(p for p in unit_dir.glob('[0-9][0-9]-*.md')
                    if not p.name.startswith('00-'))
    stories = unit_dir / 'সাহাবিদের-ঘটনা'
    if stories.is_dir():
        files += sorted(stories.glob('*.md'))
    return files


def card_list(items, css_prefix=''):
    """items: list of (title, href)."""
    icons = ['📖', '📜', '🕌', '🤲', '🧭', '⚠️', '📿', '📔', '⚖️', '🔁', '🌟', '❓']
    out = ['<ul class="card-list">']
    for idx, (title, href) in enumerate(items):
        icon = icons[idx % len(icons)]
        out.append(f'<li><a href="{href}"><span class="card-icon">{icon}</span>{esc(title)}</a></li>')
    out.append('</ul>')
    return '\n'.join(out)


def build_pages(topic_dir, md_files, unit_dir=None):
    """Build one HTML page per md file; return list of (title, href).
    href is relative to the topic index (unit_dir=None) or the unit index."""
    items = []
    for md in md_files:
        text = md.read_text(encoding='utf-8')
        title = h1_of(text, md.stem)
        body = convert(text)
        rel = md.relative_to(topic_dir)
        out_path = DOCS / topic_dir.name / rel.with_suffix('.html')
        out_path.parent.mkdir(parents=True, exist_ok=True)
        depth = len(rel.parts) - 1
        if unit_dir:
            back = '../' * (depth - 1) + 'index.html'
            href = urllib.parse.quote(str(md.relative_to(unit_dir).with_suffix('.html')), safe='/.-')
        else:
            back = '../' * depth + 'index.html'
            href = urllib.parse.quote(str(rel.with_suffix('.html')), safe='/.-')
        css_href = '../' * (depth + 1) + 'assets/style.css'
        pdf_url = raw_pdf_url(md.with_suffix('.pdf'))
        out_path.write_text(page(title, body, back_href=back, pdf_url=pdf_url, css_href=css_href),
                            encoding='utf-8')
        items.append((title, href))
        print('wrote', out_path)
    return items


def build_topic(topic_dir, brand, tagline):
    """Build per-topic pages + the topic index (supports nested confusion units)."""
    units = sorted((p for p in topic_dir.glob('[0-9][0-9]-*') if p.is_dir()))

    if units:
        # Nested structure: each unit (confusion) is an independent sub-collection.
        unit_cards = []
        for unit in units:
            unit_rel = unit.name
            md_files = unit_md_files(unit)
            items = build_pages(topic_dir, md_files, unit_dir=unit)
            index_path = DOCS / topic_dir.name / unit_rel / 'index.html'
            body = ['<blockquote class="notice">\n' + inline(NOTICE_TEXT) + '\n</blockquote>',
                    card_list(items)]
            index_path.write_text(page(unit_rel, '\n'.join(body), back_href='../../index.html',
                                       css_href='../../assets/style.css'),
                                  encoding='utf-8')
            print('wrote', index_path)
            unit_cards.append((unit_rel, urllib.parse.quote(unit_rel, safe='/-') + '/index.html'))

        index_path = DOCS / topic_dir.name / 'index.html'
        body = ['<blockquote class="notice">\n' + inline(NOTICE_TEXT) + '\n</blockquote>',
                card_list(unit_cards)]
        body.append('<p class="small">প্রতিটি দ্বিধা একটি আলাদা সাবফোল্ডার — ভেতরে কুরআন, হাদিস, ব্যবহারিক গাইড ও সাহাবিদের ঘটনা। '
                    'সবগুলো বিষয়ের PDF এই রিপোজিটরিতে আছে: '
                    f'<a href="https://github.com/ahsanjust/tazkiyah">github.com/ahsanjust/tazkiyah</a></p>')
        index_path.write_text(page(brand, '\n'.join(body), back_href='../index.html',
                                   css_href='../assets/style.css', banner=True, tagline=tagline),
                              encoding='utf-8')
        print('wrote', index_path)
        return

    # Flat structure (original behaviour).
    md_files = topic_md_files(topic_dir)
    items = build_pages(topic_dir, md_files)
    index_path = DOCS / topic_dir.name / 'index.html'
    body = ['<blockquote class="notice">\n' + inline(NOTICE_TEXT) + '\n</blockquote>',
            card_list(items)]
    body.append('<p class="small">সবগুলো বিষয়ের PDF এই রিপোজিটরিতে আছে: '
                f'<a href="https://github.com/ahsanjust/tazkiyah">github.com/ahsanjust/tazkiyah</a></p>')
    index_path.write_text(page(brand, '\n'.join(body), back_href='../index.html',
                               css_href='../assets/style.css', banner=True, tagline=tagline),
                          encoding='utf-8')
    print('wrote', index_path)


def build():
    DOCS.mkdir(exist_ok=True)
    (DOCS / '.nojekyll').write_text('', encoding='utf-8')

    # assets
    if ASSET_SRC.exists():
        ASSET_DST.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ASSET_SRC, ASSET_DST)
        print('copied', ASSET_SRC, '->', ASSET_DST)

    topic_dirs = sorted(
        (p for p in ROOT.glob('[0-9][0-9]-*') if p.is_dir() and p.name in TOPICS),
        key=lambda p: list(TOPICS).index(p.name))
    for p in sorted(ROOT.glob('[0-9][0-9]-*')):
        if p.is_dir() and p.name not in TOPICS:
            print(f'warning: skipping topic dir not in TOPICS: {p.name}')

    for topic_dir in topic_dirs:
        brand, tagline = TOPICS[topic_dir.name]
        build_topic(topic_dir, brand, tagline)

    # hub index
    hub_body = ['<blockquote class="notice">\n' + inline(NOTICE_TEXT) + '\n</blockquote>']
    hub_items = []
    for topic_dir in topic_dirs:
        brand, _tagline = TOPICS[topic_dir.name]
        href = urllib.parse.quote(topic_dir.name, safe='/-') + '/index.html'
        hub_items.append((brand, href))
    hub_body.append(card_list(hub_items))
    hub_body.append('<p class="small">প্রতিটি বিষয়ে .md (সম্পাদনা), .tex ও .pdf (আরামে পড়া) দুটি ফরম্যাটেই আছে।</p>')
    (DOCS / 'index.html').write_text(
        page('তাযকিয়াহ — শেখা ও অনুশীলনের সংকলন',
             '\n'.join(hub_body), back_href='index.html', css_href='assets/style.css',
             banner=True,
             tagline='কুরআন, সহীহ হাদিস ও সাহাবিদের জীবন্ত উদাহরণের আলোকে ধাপে ধাপে ইসলামি জ্ঞান ও চরিত্র গঠন।'),
        encoding='utf-8')
    print('wrote', DOCS / 'index.html')


if __name__ == '__main__':
    build()
