"""Look up public, annotated business episodes by mechanism or case ID (offline)."""
import argparse
import json
from pathlib import Path

BOOK = Path(__file__).resolve().parents[1] / 'references' / 'casebook.json'

def diverse(rows):
    """First look across subjects before taking their second case."""
    groups = {}
    for row in rows:
        groups.setdefault(row['subject'], []).append(row)
    for index in range(max((len(group) for group in groups.values()), default=0)):
        for group in groups.values():
            if index < len(group):
                yield group[index]

def main():
    rows = json.loads(BOOK.read_text(encoding='utf-8'))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag', action='append', default=[], help='Repeat for AND. E.g. 验证, 治理')
    parser.add_argument('--sign', choices=['正例','反例','混合'])
    parser.add_argument('--stage', choices=['起念','下注','首证','接力','续约','断点'])
    parser.add_argument('--id', nargs='+', help='Read full case cards')
    parser.add_argument('--term', help='Literal match in subject, event or annotated facts')
    parser.add_argument('--limit', type=int, default=12)
    args = parser.parse_args()
    if args.id:
        by_id = {r['id']:r for r in rows}
        missing = [i for i in args.id if i not in by_id]
        if missing:
            parser.error('Unknown case ID: '+', '.join(missing))
        print(json.dumps([by_id[i] for i in args.id], ensure_ascii=False, indent=2))
        return
    if args.limit < 1:
        parser.error('limit must be positive')
    matches = [r for r in rows if (not args.sign or r['sign']==args.sign)
               and (not args.stage or r['stage']==args.stage)
               and all(tag in r['mechanisms'] for tag in args.tag)
               and (not args.term or args.term.casefold() in
                    ' '.join(r[k] for k in ('subject','title','fact','move','limit','business_question','affected_party')).casefold())]
    print(f'{len(matches)} 条匹配 / {len(rows)} 条在库。结果仅供选读。')
    for r in list(diverse(matches))[:args.limit]:
        print(f"{r['id']}　{r['sign']}　{r['subject']} · {r['title']}　{r['stage']} / {' '.join(r['mechanisms'])}")

if __name__ == '__main__':
    main()
