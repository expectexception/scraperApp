from bs4 import BeautifulSoup

with open('scratch/avincis.html', 'r') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')

print("=== HEADINGS ===")
for h in soup.find_all(['h1', 'h2', 'h3']):
    print(f"{h.name}: {h.text.strip()}")

print("\n=== LINKS with class ===")
for a in soup.find_all('a'):
    if a.has_attr('class'):
        print(f"[{' '.join(a['class'])}] {a.text.strip()} -> {a.get('href', '')}")

print("\n=== ALL LINKS (Top 30) ===")
for a in soup.find_all('a')[:30]:
    print(f"{a.text.strip()} -> {a.get('href', '')}")
