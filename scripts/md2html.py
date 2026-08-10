#!/usr/bin/env python3
"""Convert the Bengali markdown learning files to static HTML for GitHub Pages.

Usage: python3 scripts/md2html.py
Output: docs/index.html + one .html per .md file (mirroring the topic layout).
PDFs are linked to the raw GitHub URL so they download from the public repo.
"""
import html
import os
import pathlib
import re
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOPIC = ROOT / '01-কিবর-ও-উজব'
DOCS = ROOT / 'docs'
REPO_RAW = 'https://raw.githubusercontent.com/ahsanjust/tazkiyah/main'

FONT = ('Noto Sans Bengali:400,600,700&display=swap')

NOTICE_MARK = '**গুরুত্বপূর্ণ নোটিশ'


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
    url = REPO_RAW + '/' + urllib.parse.quote(str(rel), safe='/.')
    return url


def page(title, body, back_href='index.html', pdf_url=None, css_href='assets/style.css'):
    pdf_link = f'<a class="btn" href="{pdf_url}">📥 PDF ডাউনলোড</a>' if pdf_url else ''
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
  <a class="brand" href="{back_href}">তাযকিয়াহ — অহংকার (কিবর) ও উজব</a>
</header>
<main class="wrap">
  <div class="page-head">
    <a class="back" href="{back_href}">← সূচীপত্রে ফিরুন</a>
    <h1>{esc(title)}</h1>
    {pdf_link}
  </div>
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


def h1_of(md_text):
    for line in md_text.split('\n'):
        if line.startswith('# '):
            return line[2:].strip()
    return pathlib.Path(md_text).stem


def build():
    DOCS.mkdir(exist_ok=True)

    md_files = [
        TOPIC / 'কুরআন/01-কুরআনের-আয়াত.md',
        TOPIC / 'হাদিস/02-হাদিস-ও-আসার.md',
        TOPIC / '03-ব্যবহারিক-গাইড.md',
    ] + sorted((TOPIC / 'সাহাবিদের-ঘটনা').glob('*.md'))

    items = []
    for md in md_files:
        text = md.read_text(encoding='utf-8')
        title = h1_of(text)
        body = convert(text)
        rel = md.relative_to(TOPIC)
        html_name = rel.with_suffix('.html')
        out_path = DOCS / html_name
        out_path.parent.mkdir(parents=True, exist_ok=True)
        depth = len(rel.parts) - 1
        back = '../' * depth + 'index.html'
        css_href = '../' * depth + 'assets/style.css'
        href = urllib.parse.quote(str(html_name), safe='/.')
        pdf_url = raw_pdf_url(md.with_suffix('.pdf'))
        out_path.write_text(page(title, body, back_href=back, pdf_url=pdf_url, css_href=css_href),
                            encoding='utf-8')
        items.append((title, href))
        print('wrote', out_path)

    home_body = []
    home_body.append('<blockquote class="notice">\n' +
                     inline('**গুরুত্বপূর্ণ নোটিশ (Important Notice):** এই কন্টেন্টটি AI (কৃত্রিম বুদ্ধিমত্তা) দিয়ে প্রস্তুত ও সংকলিত। AI কঠোর সূত্র-মান নীতি মেনে শুধু নির্ভরযোগ্য উৎস থেকে তথ্য সংগ্রহ করেছে — কেবল সহীহ/হাসান হাদিস ও সহীহ সনদের আসার রাখা হয়েছে, দুর্বল সনদ বাদ দেওয়া হয়েছে। তবে এটি কোনো আলেম বা মুহাদ্দিস কর্তৃক যাচাইকৃত নয়।') +
                     '\n</blockquote>')
    home_body.append('<p>কিবর ও উজব বোঝার ও তা থেকে বাঁচার পূর্ণাঙ্গ সংকলন — কুরআনের আয়াত, সহীহ হাদিস ও সাহাবিদের ঘটনা।</p>')
    home_body.append('<ul class="card-list">')
    for title, href in items:
        home_body.append(f'<li><a href="{href}">{esc(title)}</a></li>')
    home_body.append('</ul>')
    home_body.append('<p class="small">সবগুলো বিষয়ের PDF এই রিপোজিটরিতে আছে: '
                     '<a href="https://github.com/ahsanjust/tazkiyah">github.com/ahsanjust/tazkiyah</a></p>')

    index = page('সূচীপত্র', '\n'.join(home_body), back_href='index.html')
    (DOCS / 'index.html').write_text(index, encoding='utf-8')
    (DOCS / '.nojekyll').write_text('', encoding='utf-8')
    print('wrote', DOCS / 'index.html')
    print('wrote', DOCS / '.nojekyll')


if __name__ == '__main__':
    build()
