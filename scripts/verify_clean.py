import urllib.request

base = 'http://127.0.0.1:5000'

# Index
resp = urllib.request.urlopen(f'{base}/', timeout=5)
html = resp.read().decode()
print('Index.html:')
print(f'  manifest link: {"PASS" if "manifest.json" in html else "FAIL"}')
print(f'  SW register script: {"PASS" if "pwa-register.js" in html else "FAIL"}')
print(f'  favicon: {"PASS" if "favicon.ico" in html else "FAIL"}')
print(f'  apple-touch-icon: {"PASS" if "apple-touch-icon" in html else "FAIL"}')
print(f'  theme-color meta: {"PASS" if "theme-color" in html else "FAIL"}')
print(f'  no loader-wrapper: {"PASS" if "loader-wrapper" not in html else "FAIL"}')
print(f'  video preload=auto: {"PASS" if "preload=" in html else "FAIL"}')
print(f'  video autoplay: {"PASS" if "autoplay" in html else "FAIL"}')
print(f'  pwa.css loaded: {"PASS" if "pwa.css" in html else "FAIL"}')

# BrowseCars
resp = urllib.request.urlopen(f'{base}/cars/browse', timeout=5)
html = resp.read().decode()
print('\nBrowseCars.html:')
print(f'  manifest: {"PASS" if "manifest.json" in html else "FAIL"}')
print(f'  SW register: {"PASS" if "pwa-register.js" in html else "FAIL"}')
print(f'  no loader-wrapper: {"PASS" if "loader-wrapper" not in html else "FAIL"}')

# All pages
for path, name in [('/about', 'About'), ('/auth/login', 'Login'), ('/profile', 'Profile'), ('/offline', 'Offline'), ('/cars/browse', 'BrowseCars')]:
    resp = urllib.request.urlopen(f'{base}{path}', timeout=5)
    html = resp.read().decode()
    has_pwa = 'manifest.json' in html and 'pwa-register.js' in html
    print(f'  {name} ({path}): {"PASS" if has_pwa else "FAIL"}')
