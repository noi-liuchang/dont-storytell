"""Render one offline narrative strategy from a small UTF-8 JSON file."""
import argparse
import html
import json
from pathlib import Path
from urllib.parse import urlsplit

STYLES = """
:root{color-scheme:light;--ink:#201f1d;--muted:#5c5b55;--line:#c9c6bd}
*{box-sizing:border-box}body{margin:0;background:#eae8e1;color:var(--ink);font:16px/1.65 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}main{max-width:900px;margin:36px auto;background:#fffefb;padding:42px 58px}
header,footer{display:flex;gap:12px;justify-content:space-between;align-items:baseline;font-size:12px;color:var(--muted);letter-spacing:.04em}header{border-top:3px solid var(--ink);padding-top:10px}
h1{font-size:38px;line-height:1.22;margin:22px 0}h2{font-size:17px;line-height:1.4;margin:0 0 8px}h2 b{display:inline-block;min-width:35px;color:var(--muted);font:13px/1.6 ui-monospace,monospace}
section{border-top:1px solid var(--line);padding:15px 0}p{margin:5px 0}section:first-of-type strong{font-size:23px;line-height:1.48}ul{margin:3px 0;padding-left:21px}li+li{margin-top:3px}table{width:100%;border-collapse:collapse;text-align:left;font-size:14px}th{font-size:12px;color:var(--muted);font-weight:600}td,th{padding:6px 8px 6px 0;vertical-align:top;border-bottom:1px solid #dedcd5}td:first-child{width:19%;font-weight:600}td:last-child{width:30%}
footer{display:block;border-top:2px solid var(--ink);padding-top:10px;letter-spacing:0}a{color:inherit;text-decoration:underline;text-underline-offset:.17em}a+a{margin-left:12px}p,li,td,a{overflow-wrap:anywhere}
aside{margin:6px 0 18px;padding:12px 16px;border-left:3px solid var(--ink);background:#f1f0ea}aside h2{font-size:15px}
button{margin:5px 10px 0 0;padding:5px 10px;color:inherit;border:1px solid var(--ink);background:transparent;cursor:pointer}button:focus-visible{outline:2px solid var(--ink);outline-offset:2px}[role=status]{font-size:13px}
@media print{aside{break-inside:avoid;margin-bottom:8px}aside button,aside [role=status]{display:none}}
@media(max-width:600px){main{margin:0;padding:22px 19px}h1{font-size:29px}section:first-of-type strong{font-size:21px}td,th{padding-right:5px}header{align-items:flex-start}}
@page{size:A4;margin:13mm 15mm}@media print{body{background:white;font-size:10pt;line-height:1.5}main{max-width:none;margin:0;padding:0}header,footer{font-size:8pt}h1{font-size:24pt;margin:12px 0}h2{font-size:12pt}section{padding:9px 0;break-inside:avoid}section:first-of-type strong{font-size:16pt}table{font-size:9pt}td,th{padding:4px 6px 4px 0}}
"""

STYLES += """
.story{border-top:1px solid var(--line);padding:12px 0 18px}.story p{margin:0 0 13px}.story .lead{font-size:21px;line-height:1.6;margin-bottom:16px}.story h2{font-size:17px;margin-top:19px}.step{border-left:3px solid var(--ink);padding:5px 0 2px 14px;margin-top:18px}.step b{font-size:13px;color:var(--muted)}.step p{margin:2px 0}.editor-note{font-size:13px;color:var(--muted);margin:0 0 12px}@media print{.story{padding:10px 0;font-size:12pt;line-height:1.68}.story .lead{font-size:15pt}.story p{margin-bottom:8px}.story h2{font-size:13pt;margin-top:15px}.editor-note{font-size:9pt}}
"""
COPY_SCRIPT = """
<script>
document.querySelector('#copy-note').addEventListener('click', async () => {
  const note = document.querySelector('#share-note');
  const status = document.querySelector('#copy-status');
  try {
    await navigator.clipboard.writeText(note.textContent);
    status.textContent = '已复制';
  } catch {
    const range = document.createRange();
    range.selectNodeContents(note);
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
    status.textContent = '文字已选中，请手动复制';
  }
});
</script>
"""

def escape(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Expected nonempty text")
    return html.escape(value)

def section(index, name, content):
    return f'<section><h2><b>{index:02}</b>{name}</h2>{content}</section>'

def bullets(values):
    if not isinstance(values, list) or not values:
        raise ValueError("Expected one or more entries")
    return '<ul>' + ''.join(f'<li>{escape(v)}</li>' for v in values) + '</ul>'

def source_link(source):
    label = escape(source['label'])
    url = source.get('url', '')
    if not url:
        return f'<span>{label}　</span>'
    if urlsplit(url).scheme not in ('https', 'http'):
        raise ValueError("Use a public or access-controlled HTTP(S) source link, or a label only")
    return f'<a href="{escape(url)}">{label}</a>'

def legacy_sections(d):
    choices = d['choices']
    if not isinstance(choices, list) or not choices:
        raise ValueError("Expected a concrete choice or conditional choice")
    rows = []
    for choice in choices:
        cells = ''.join(f'<td>{escape(choice[k])}</td>' for k in ('choice', 'decision', 'cost'))
        rows.append(f'<tr>{cells}</tr>')
    table = '<table><thead><tr><th>面对的选择</th><th>建议怎么做</th><th>代价与承担者</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table>'
    opening = f"<p><strong>{escape(d['claim'])}</strong></p><p>{escape(d['story'])}</p>"
    if d.get('alternative'):
        opening += f"<p>{escape(d['alternative'])}</p>"
    return ''.join([
        section(1, '我怎么看', opening),
        section(2, '判断的依据', bullets(d['evidence'])),
        section(3, '眼前的取舍', table),
        section(4, '谁能改变结果', bullets(d['people'])),
        section(5, '下一步与蓄势', f"<p>{escape(d['next'])}</p><p><b>留下什么</b>　{escape(d['accumulation'])}</p>")
    ])


def strategy_sections(d):
    titles = d.get('section_titles', ['值得追的 Vision', '推荐的路', '故事序列', '谁让这条路走下去', '第一次履约'])
    if not isinstance(titles, list) or len(titles) != 5:
        raise ValueError('Expected five section titles')
    titles = [escape(title) for title in titles]
    chapters = d['chapters']
    if not isinstance(chapters, list) or not chapters:
        raise ValueError('Expected at least one event or verification step')
    acts = []
    for chapter in chapters:
        event = escape(chapter['event'])
        witness = escape(chapter['witness'])
        opens = escape(chapter['opens'])
        acts.append(f'<li><b>{event}</b>　{witness} {opens}</li>')
    return ''.join([
        section(1, titles[0], f"<p><strong>{escape(d['vision'])}</strong></p><p>{escape(d['basis'])}</p>"),
        section(2, titles[1], f"<p>{escape(d['route'])}</p>"),
        section(3, titles[2], '<ol>' + ''.join(acts) + '</ol>'),
        section(4, titles[3], f"<p>{escape(d['support'])}</p>"),
        section(5, titles[4], f"<p>{escape(d['next'])}</p><p><b>怎样判断</b>　{escape(d['review'])}</p>")
    ])


def story_page(d):
    parts = d['passages']
    if not isinstance(parts, list) or not parts:
        raise ValueError('Expected at least one story passage')
    body = [f'<article class="story"><p class="lead">{escape(d["opening"])}</p>']
    for part in parts:
        if part.get('heading'):
            body.append(f'<h2>{escape(part["heading"])}</h2>')
        body.append(f'<p>{escape(part["text"])}</p>')
    body.append(f'<div class="step"><b>下一步</b><p>{escape(d["next"])}</p></div></article>')
    if d.get('note'):
        body.append(f'<p class="editor-note">{escape(d["note"])}</p>')
    return ''.join(body)

def render(d):
    title = escape(d['title'])
    version = d.get('schema', 1)
    if version == 3:
        body = story_page(d)
    elif version == 2:
        body = strategy_sections(d)
    elif version == 1:
        body = legacy_sections(d)
    else:
        raise ValueError('Unsupported strategy schema')
    if d.get('share_note'):
        body += (f'<aside><h2>留给亲历者的一句话</h2><p id="share-note">{escape(d["share_note"])}</p>'
                 '<button type="button" id="copy-note">复制这一段</button><span role="status" id="copy-status"></span></aside>'
                 + COPY_SCRIPT)
    sources=''.join(source_link(s) for s in d.get('sources',[]))
    return f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{title}</title><style>{STYLES}</style><main><header><span>NOI　/　系统叙事工程</span><span>{escape(d["status"])}</span></header><h1>{title}</h1>{body}<footer>{sources}</footer></main></html>'

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    page=render(json.loads(args.input.read_text(encoding='utf-8')))
    args.output.write_text(page,encoding='utf-8')
