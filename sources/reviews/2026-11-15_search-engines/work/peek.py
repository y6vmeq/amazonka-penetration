"""Показывает текст вокруг ключевых слов в сырой копии: python -I work/peek.py <шаблон имени> <слово> [ширина] [макс]. Результат — в work/peek.txt."""
import html, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
def text_of(path):
    data = path.read_bytes()
    for enc in ('utf-8', 'cp1251'):
        try:
            s = data.decode(enc); break
        except UnicodeDecodeError:
            continue
    else:
        s = data.decode('utf-8', 'replace')
    t = re.sub(r'(?is)<script.*?</script>|<style.*?</style>', ' ', s)
    t = html.unescape(re.sub(r'<[^>]+>', ' ', t))
    return s, re.sub(r'\s+', ' ', t)
def main():
    name, pat = sys.argv[1], sys.argv[2]
    width = int(sys.argv[3]) if len(sys.argv) > 3 else 600
    maxhits = int(sys.argv[4]) if len(sys.argv) > 4 else 5
    out = []
    for path in sorted((HERE.parent / 'raw').glob(name)):
        s, t = text_of(path)
        hits = [m.start() for m in re.finditer(pat, t, flags=re.I)]
        out.append(f'== {path.name} len={len(s)} textlen={len(t)} hits={len(hits)}')
        for h in hits[:maxhits]:
            out.append('   ' + t[max(0, h - width // 3):h + width])
        if not hits:
            out.append('   START: ' + t[:width])
    (HERE / 'peek.txt').write_text('\n'.join(out), encoding='utf-8')
main()
