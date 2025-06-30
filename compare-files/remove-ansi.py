import re

ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
# with open('Compare-files/diffs.txt', 'r') as infile, open('Compare-files/diffs_clean.txt', 'w') as outfile:
with open('diffs.txt', 'r') as infile, open('diffs_clean1.txt', 'w') as outfile:
    for line in infile:
        clean_line = ansi_escape.sub('', line)
        outfile.write(clean_line)
