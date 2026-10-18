"""Verify imported source preservation, Python syntax and publication exclusions."""
from pathlib import Path
import ast
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)

def tree(ref):
    result = {}
    for record in git('ls-tree', '-r', '-z', ref).split(b'\0'):
        if not record:
            continue
        metadata, name = record.split(b'\t', 1)
        result[name.decode()] = metadata.decode()
    return result

def main():
    sources = json.loads((ROOT / 'docs/SOURCE_SNAPSHOTS.json').read_text())
    result = {'snapshots': [], 'python_files': 0, 'errors': []}
    for source in sources['snapshots']:
        original = tree(source['source_commit'])
        current = tree('HEAD:' + source['path'])
        allowed = set(source['intentional_changes'])
        different = sorted(name for name in original.keys() | current.keys()
                           if original.get(name) != current.get(name))
        unexpected = sorted(set(different) - allowed)
        result['snapshots'].append({'path': source['path'], 'files': len(original),
                                     'source_commit': source['source_commit'],
                                     'documented_changes': different, 'unexpected_changes': unexpected})
        result['errors'].extend(source['path'] + '/' + name for name in unexpected)
    for raw in git('ls-files', '-z').split(b'\0'):
        if not raw:
            continue
        name = raw.decode()
        path = ROOT / name
        if any(part in {'.private', '.pdf-tools', 'node_modules', '.pixi', 'check-config'} for part in path.relative_to(ROOT).parts):
            result['errors'].append('Local-only file tracked: ' + name)
        if path.stat().st_size >= 100 * 1024 * 1024:
            result['errors'].append('Oversized Git blob: ' + name)
        if path.suffix in {'.py', '.FCMacro'}:
            result['python_files'] += 1
            try:
                ast.parse(path.read_text(encoding='utf-8-sig'), filename=name)
            except (SyntaxError, UnicodeError) as exc:
                result['errors'].append(str(exc))
    result['passed'] = not result['errors']
    print(json.dumps(result, indent=2))
    return 0 if result['passed'] else 1

if __name__ == '__main__':
    sys.exit(main())
