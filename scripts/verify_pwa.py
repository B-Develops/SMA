import urllib.request

base = 'http://127.0.0.1:5000'
resp = urllib.request.urlopen(f'{base}/', timeout=5)
html = resp.read().decode()

checks = [
    ('manifest link', 'manifest.json' in html),
    ('SW register script', 'pwa-register.js' in html),
    ('video-loader wrapper', 'video-loader' in html),
    ('video-placeholder', 'video-placeholder' in html),
    ('video preload=auto (not none)', 'preload="auto"' in html),
    ('no data-src on video source', 'data-src' not in html.split('heroVideo')[0].split('</video>')[0] if 'heroVideo' in html else True),
    ('loader-wrapper-loading class', 'loader-wrapper-loading' in html),
    ('loader-skeleton span', 'loader-skeleton' in html),
    ('loader-spinner span', 'loader-spinner' in html),
    ('video-hidden/video-visible classes', 'video-hidden' in html),
    ('pwa CSS loaded', 'pwa.css' in html),
    ('install hint logic in JS', 'isMobile' in html),
]

for name, result in checks:
    print(f'  [{"PASS" if result else "FAIL"}] {name}')

resp = urllib.request.urlopen(f'{base}/cars/browse', timeout=5)
html = resp.read().decode()
print()
print(f'BrowseCars: {"PASS" if resp.status == 200 else "FAIL"}')

for r in [('/about', 'About'), ('/auth/login', 'Login'), ('/profile', 'Profile'), ('/offline', 'Offline')]:
    try:
        resp = urllib.request.urlopen(f'{base}{r[0]}', timeout=5)
        has_pwa = 'manifest.json' in resp.read().decode()
        print(f'  {r[1]} ({r[0]}): {resp.status} | PWA head: {has_pwa}')
    except Exception as e:
        if '401' in str(e) or '403' in str(e) or '302' in str(e):
            print(f'  {r[1]} ({r[0]}): requires auth (expected)')
        else:
            print(f'  {r[1]} ({r[0]}): ERROR - {e}')
