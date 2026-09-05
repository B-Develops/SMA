"""Add PWA head include to all user-facing HTML templates."""
import os
import glob

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), '..', 'app', 'templates')

SKIP = {
    'offline.html',  # Already has hardcoded PWA elements
    'test.html',
    'test2.html',
}

SKIP_DIRS = {'email'}

INCLUDE_LINE = '    {% include \'_pwa_head.html\' %}\n'

count = 0
for filepath in glob.glob(os.path.join(TEMPLATES_DIR, '**', '*.html'), recursive=True):
    relpath = os.path.relpath(filepath, TEMPLATES_DIR)
    parts = relpath.split(os.sep)
    filename = parts[-1]

    if filename in SKIP:
        continue
    if parts[0] in SKIP_DIRS if len(parts) > 1 else False:
        continue

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    if '_pwa_head' in content or 'manifest' in content:
        continue

    # Find </head> and insert before it
    placeholder = '  </head>'
    if placeholder in content:
        content = content.replace(placeholder, INCLUDE_LINE + placeholder, 1)
    elif '</head>' in content:
        content = content.replace('</head>', INCLUDE_LINE + '</head>', 1)
    else:
        print(f'  WARNING: No </head> found in {relpath}')
        continue

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    count += 1
    print(f'  Updated: {relpath}')

print(f'\nTotal: {count} templates updated.')
