
from pathlib import Path
from rich.console import Console

console: Console = Console()

code_linecount: int = 0
data_linecount: int = 0
text_linecount: int = 0

code_filecount: int = 0
data_filecount: int = 0
text_filecount: int = 0

find_files = lambda pattern: filter(
    lambda p: 'venv' not in str(p) and '.agents' not in str(p) and 'testing_reports' not in str(p), Path('.').rglob(pattern)
)

codefiles = list(find_files('*.py'))
datafiles = list(find_files('*.json')) + list(find_files('*.yaml'))
textfiles = list(find_files('*.txt')) + list(find_files('*.md'))

for file_path in codefiles:
    with open(file_path, 'r', encoding='utf-8') as file:
        code_filecount += 1
        code_linecount += len(file.readlines())

for file_path in datafiles:
    with open(file_path, 'r', encoding='utf-8') as file:
        data_filecount += 1
        data_linecount += len(file.readlines())

for file_path in textfiles:
    with open(file_path, 'r', encoding='utf-8') as file:
        text_filecount += 1
        text_linecount += len(file.readlines())

console.print(f"Code lines: {code_linecount:,} in {code_filecount:,} files")
console.print(f"Data lines: {data_linecount:,} in {data_filecount:,} files")
console.print(f"Text lines: {text_linecount:,} in {text_filecount:,} files")

console.print()
console.print("All files:")
for file_path in codefiles + datafiles + textfiles:
    console.print(file_path)
