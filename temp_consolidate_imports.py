from pathlib import Path
import re

file_path = Path('models/forecaster_pro.ipynb')
text = file_path.read_text(encoding='utf-8')
# split into cells by closing tag
cells = re.split(r'(</VSCode\.Cell>)', text)
parsed = []
for i in range(0, len(cells) - 1, 2):
    body = cells[i]
    close = cells[i + 1]
    parsed.append(body + close)
if len(cells) % 2 == 1:
    parsed.append(cells[-1])

import_block_re = re.compile(r'^\s*(import |from )')
imports = []
seen = set()
for cell in parsed:
    if 'language="python"' not in cell:
        continue
    lines = cell.splitlines(True)
    i = 0
    while i < len(lines):
        line = lines[i]
        if import_block_re.match(line) and not line.lstrip().startswith('#'):
            block = [line]
            if line.rstrip().endswith('('):
                j = i + 1
                while j < len(lines):
                    block.append(lines[j])
                    if lines[j].strip().endswith(')'):
                        i = j
                        break
                    j += 1
            elif line.rstrip().endswith('\\'):
                j = i + 1
                while j < len(lines) and lines[j-1].rstrip().endswith('\\'):
                    block.append(lines[j])
                    j += 1
                i = j - 1
            full_block = ''.join(block)
            if full_block not in seen:
                seen.add(full_block)
                imports.append(full_block)
        i += 1

# find first python cell index
first_python_idx = next((i for i, c in enumerate(parsed) if 'language="python"' in c), None)
if first_python_idx is None:
    raise SystemExit('No python cells found')

orig_cell0 = parsed[first_python_idx]
lines = orig_cell0.splitlines(True)
new_lines = []
import_found = False
for line in lines:
    if import_block_re.match(line) and not line.lstrip().startswith('#'):
        import_found = True
        continue
    if import_found and not line.strip():
        continue
    new_lines.append(line)

unique_imports = imports
new_cell0 = ''.join(new_lines)
if new_cell0.startswith('#'):
    parts = new_cell0.split('\n', 1)
    if len(parts) > 1:
        new_cell0 = parts[0] + '\n' + ''.join(unique_imports) + '\n' + parts[1]
    else:
        new_cell0 = new_cell0 + ''.join(unique_imports) + '\n'
else:
    new_cell0 = ''.join(unique_imports) + '\n' + new_cell0
parsed[first_python_idx] = new_cell0

for idx, cell in enumerate(parsed):
    if idx == first_python_idx or 'language="python"' not in cell:
        continue
    lines = cell.splitlines(True)
    new_cell = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if import_block_re.match(line) and not line.lstrip().startswith('#'):
            if line.rstrip().endswith('('):
                i += 1
                while i < len(lines) and not lines[i].strip().endswith(')'):
                    i += 1
                i += 1
                continue
            if line.rstrip().endswith('\\'):
                i += 1
                while i < len(lines) and lines[i-1].rstrip().endswith('\\'):
                    i += 1
                continue
            i += 1
            continue
        new_cell.append(line)
        i += 1
    parsed[idx] = ''.join(new_cell)

file_path.write_text(''.join(parsed), encoding='utf-8')
print('ok')
