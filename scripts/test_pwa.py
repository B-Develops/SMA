import urllib.request

base = 'http://127.0.0.1:5000'

tests = []

# Test Index page
resp = urllib.request.urlopen(f'{base}/', timeout=5)
html = resp.read().decode()
tests.append(('Index status', resp.status == 200))
tests.append(('Has manifest', 'manifest.json' in html))
tests.append(('Has SW register', 'pwa-register.js' in html))
tests.append(('Has video-loader', 'video-loader' in html))
tests.append(('Has loader-wrapper', 'loader-wrapper' in html))
tests.append(('Preload none', 'preload="none"' in html))
tests.append(('data-src on source', 'data-src' in html))

# Test static assets
for path in ['/static/manifest.json', '/static/sw.js', '/static/pwa.css', '/static/pwa-register.js']:
    try:
        r = urllib.request.urlopen(f'{base}{path}', timeout=5)
        tests.append((f'{path} status', r.status == 200))
    except Exception as e:
        tests.append((f'{path} status', False))

# Test icon
try:
    r = urllib.request.urlopen(f'{base}/static/icons/icon-192.png', timeout=5)
    tests.append(('icon-192.png status', r.status == 200))
except Exception:
    tests.append(('icon-192.png status', False))

# Test offline page
resp = urllib.request.urlopen(f'{base}/offline', timeout=5)
html = resp.read().decode()
tests.append(('Offline page', resp.status == 200))
tests.append(('Offline has manifest', 'manifest.json' in html))

# Test other templates render
for path in ['/about', '/cars', '/auth/login']:
    try:
        r = urllib.request.urlopen(f'{base}{path}', timeout=5)
        tests.append((f'{path} renders', r.status == 200))
    except Exception:
        tests.append((f'{path} renders', False))

passed = sum(1 for _, ok in tests if ok)
total = len(tests)
for name, ok in tests:
    status = 'PASS' if ok else 'FAIL'
    print(f'  [{status}] {name}')
print(f'\n{passed}/{total} tests passed')
