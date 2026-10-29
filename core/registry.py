from core.storage import ROOT, load
CLAIMS = load(ROOT / 'data/claims.json')
PAGES = {
 'X1': ['B1'], '1': ['B3'], '2a': ['B2'], '2b': ['B4'],
 '3a': ['B5'], '3b': ['B6'], '3c': ['B7'], '4a': ['B8'], '4b': ['B8'],
 '4c': ['B9'], '5+6': ['B10'], '7': ['B11'], 'X2': ['B12'],
 'X3': ['B13'], 'E2E': ['B14'],
}
