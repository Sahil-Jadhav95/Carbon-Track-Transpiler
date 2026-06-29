import urllib.request
import urllib.parse
import json

queries = ['green software engineering', 'energy efficiency python programming', 'codecarbon energy', 'AST refactoring energy']

results = []
for q in queries:
    url = f'https://api.crossref.org/works?query={urllib.parse.quote(q)}&filter=from-pub-date:2022,until-pub-date:2024,type:journal-article&select=DOI,title,author,issued,container-title&rows=5'
    req = urllib.request.Request(url, headers={'User-Agent': 'mailto:test@example.com'})
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            for item in data['message']['items']:
                results.append(item)
    except Exception as e:
        pass

with open('references.bib', 'w', encoding='utf-8') as f:
    for i, r in enumerate(results):
        title = r.get('title', [''])[0]
        authors = ' and '.join([a.get('family', '') + ', ' + a.get('given', '') for a in r.get('author', [])])
        year_data = r.get('issued', {}).get('date-parts', [[None]])[0]
        year = year_data[0] if year_data else '2023'
        venue = r.get('container-title', [''])[0]
        f.write(f"@article{{ref{i+1},\n")
        f.write(f"  title={{{title}}},\n")
        f.write(f"  author={{{authors}}},\n")
        f.write(f"  journal={{{venue}}},\n")
        f.write(f"  year={{{year}}}\n")
        f.write(f"}}\n\n")

print("Saved references to references.bib")
