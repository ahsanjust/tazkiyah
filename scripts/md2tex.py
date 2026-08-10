#!/usr/bin/env python3
"""Convert the Bengali/Arabic markdown learning files to LaTeX for LuaLaTeX.

Usage: python3 scripts/md2tex.py <input.md> <output.tex> [title]
The preamble is read from shared/preamble.tex (relative to this script).
English/Latin runs are wrapped in \\lat{...} because the Bengali fonts lack
Latin glyphs; Arabic runs in \\arab{...}; arrows/quotes are mapped to safe
LaTeX so no character is silently dropped from the PDF.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PREAMBLE_PATH = os.path.join(HERE, '..', 'shared', 'preamble.tex')

ARABIC_RE = re.compile(r'[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]+')
ARABIC_PUNCT = 'ۖۗۘۙۚۛۜ'
LATIN_RE = re.compile(r"(?<!\\)[A-Za-z0-9]+(?:['\u2019-][A-Za-z0-9]+)*")


def has_arabic(s):
    return bool(ARABIC_RE.search(s))


def wrap_arabic(text):
    def _w(m):
        return r'\arab{' + m.group(0) + '}'
    return ARABIC_RE.sub(_w, text)


def wrap_latin(text):
    def _w(m):
        return r'\lat{' + m.group(0) + '}'
    return LATIN_RE.sub(_w, text)


def inline(text):
    """Convert inline markdown (**bold**, *italic*) to LaTeX, wrapping Latin/Arabic."""
    text = text.replace('\\', r'\textbackslash{}')
    text = text.replace('⚠️', '').replace('⚠', '')
    text = text.replace('#', r'\#').replace('%', r'\%').replace('&', r'\&')
    text = text.replace('_', r'\_').replace('$', r'\$')
    # Latin runs -> \lat{...} (before bold so command names stay untouched)
    text = wrap_latin(text)
    # bold
    text = re.sub(r'\*\*(.+?)\*\*', r'\\textbf{\1}', text)
    # italic
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'\\textit{\1}', text)
    # arrows and quotes that the Bengali font lacks
    text = text.replace('→', r'$\rightarrow$')
    text = text.replace('«', r'\lat{“}')
    text = text.replace('»', r'\lat{”}')
    return wrap_arabic(text)


def wrap_line_arabic(text):
    """True if a line is wholly/mostly Arabic (full Quran verse)."""
    stripped = text.replace('*', '').replace('«', '').replace('»', '').strip()
    if not stripped:
        return False
    arab = re.sub(r'[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF\u0660-\u0669.,;:\s'
                  + ARABIC_PUNCT + r'\u0300-\u036F\u064B-\u065F\u0670\u06D6-\u06ED\u0640«»]+', '', stripped)
    return has_arabic(stripped) and not arab.strip()


def convert_line(line):
    line = line.rstrip('\n')
    if not line.strip():
        return ''
    stripped = line.strip()

    if stripped.startswith('# '):
        return '\\section*{' + inline(stripped[2:]) + '}'
    if stripped.startswith('## '):
        return '\\subsection*{' + inline(stripped[3:]) + '}'
    if stripped.startswith('### '):
        return '\\subsubsection*{' + inline(stripped[4:]) + '}'

    if re.match(r'^---+$', stripped):
        return '\\medskip\\hrule\\medskip'

    return inline(stripped)


def convert(text):
    lines = text.split('\n')
    out = []
    in_list = None
    in_table = False
    table_rows = []
    i = 0

    def close_list():
        nonlocal in_list
        if in_list:
            out.append('\\end{' + in_list + '}')
            in_list = None

    def flush_table():
        nonlocal in_table, table_rows
        if in_table:
            ncols = len(table_rows[0])
            out.append('\\begin{table}[h]\\centering\\small')
            out.append('\\begin{tabular}{' + 'l' * ncols + '}')
            for ri, row in enumerate(table_rows):
                cells = [inline(c.strip()) for c in row]
                out.append(' & '.join(cells) + r' \\')
                if ri == 0:
                    out.append('\\hline')
            out.append('\\hline')
            out.append('\\end{tabular}')
            out.append('\\end{table}')
            table_rows = []
            in_table = False

    def is_quote(line):
        s = line.strip()
        return s == '>' or s.startswith('> ')

    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip('\n')
        stripped = line.strip()

        # --- tables ---
        if stripped.startswith('|'):
            cells = [c for c in stripped.strip('|').split('|')]
            if all(re.match(r'^[-:\s]+$', c) for c in cells):
                i += 1
                continue
            if not in_table:
                flush_table()
                close_list()
                in_table = True
            table_rows.append(cells)
            i += 1
            continue
        if in_table:
            flush_table()

        # --- blockquotes: group consecutive '>' lines ---
        if is_quote(line):
            close_list()
            qlines = []
            while i < len(lines) and is_quote(lines[i]):
                content = lines[i].strip()
                content = content[1:].strip() if content.startswith('>') else content
                qlines.append(content)
                i += 1
            inner = ' \\\\\n'.join(inline(q) for q in qlines if q)
            if any('**গুরুত্বপূর্ণ নোটিশ' in q for q in qlines):
                out.append('\\begin{warnbox}\n' + inner + '\n\\end{warnbox}')
            else:
                out.append('\\begin{quote}\n' + inner + '\n\\end{quote}')
            continue

        # --- lists ---
        m_ol = re.match(r'^(\d+)\.\s+(.*)$', stripped)
        m_ul = re.match(r'^[-*]\s+(.*)$', stripped)
        if m_ol:
            if in_list != 'enumerate':
                close_list()
                out.append('\\begin{enumerate}')
                in_list = 'enumerate'
            out.append('\\item ' + inline(m_ol.group(2)))
            i += 1
            continue
        if m_ul:
            if in_list != 'itemize':
                close_list()
                out.append('\\begin{itemize}')
                in_list = 'itemize'
            out.append('\\item ' + inline(m_ul.group(1)))
            i += 1
            continue

        if in_list and stripped == '':
            close_list()
            i += 1
            continue
        if in_list and not m_ol and not m_ul and stripped:
            close_list()

        # --- full-line Arabic (Quran verse) ---
        if wrap_line_arabic(line):
            body = line.replace('**', '')
            out.append('\\begin{center}\\arab{' + body + '}\\end{center}')
            i += 1
            continue

        out.append(convert_line(line))
        i += 1

    close_list()
    flush_table()
    return '\n'.join(out)


def main():
    src = sys.argv[1]
    dst = sys.argv[2]
    title = sys.argv[3] if len(sys.argv) > 3 else os.path.basename(src)

    with open(src, encoding='utf-8') as f:
        content = f.read()

    pre_path = os.path.relpath(PREAMBLE_PATH, os.path.dirname(os.path.abspath(dst)))
    body = convert(content)
    full = '\\input{' + pre_path + '}\n'
    full += '\\begin{document}\n'
    full += '\\begin{center}{\\Large\\bfseries\\color{emerald} ' + title.replace('_', ' ') + '}\\end{center}\n\\vspace{1em}\n'
    full += body + '\n\n\\end{document}\n'

    with open(dst, 'w', encoding='utf-8') as f:
        f.write(full)
    print(f'wrote {dst}')


if __name__ == '__main__':
    main()
