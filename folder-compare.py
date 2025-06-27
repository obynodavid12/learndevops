#!/usr/bin/env python3
import sys, os, difflib, argparse
from datetime import datetime, timezone

def color_diff(diff_lines):
    for line in diff_lines:
        if line.startswith('+'):
            yield f"\033[32m{line}\033[0m"  # Green
        elif line.startswith('-'):
            yield f"\033[31m{line}\033[0m"  # Red
        elif line.startswith('!') or line.startswith('?'):
            yield f"\033[33m{line}\033[0m"  # Yellow
        else:
            yield line

def file_mtime(path):
    t = datetime.fromtimestamp(os.stat(path).st_mtime, timezone.utc)
    return t.astimezone().isoformat()

def collect_files(root_dir):
    files = {}
    for dirpath, _, filenames in os.walk(root_dir):
        for f in filenames:
            full_path = os.path.join(dirpath, f)
            rel_path = os.path.relpath(full_path, root_dir)
            files[rel_path] = full_path
    return files

def compare_files(file1, file2, options):
    fromdate = file_mtime(file1)
    todate = file_mtime(file2)
    with open(file1) as ff:
        fromlines = ff.readlines()
    with open(file2) as tf:
        tolines = tf.readlines()

    if options.u:
        diff = difflib.unified_diff(fromlines, tolines, file1, file2, fromdate, todate, n=options.lines)
    elif options.n:
        diff = difflib.ndiff(fromlines, tolines)
    elif options.m:
        return [difflib.HtmlDiff().make_file(fromlines, tolines, file1, file2, context=options.c, numlines=options.lines)]
    else:
        diff = difflib.context_diff(fromlines, tolines, file1, file2, fromdate, todate, n=options.lines)

    return color_diff(diff)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', action='store_true', help='Context format diff')
    parser.add_argument('-u', action='store_true', help='Unified format diff')
    parser.add_argument('-m', action='store_true', help='HTML side-by-side diff')
    parser.add_argument('-n', action='store_true', help='Ndiff format diff')
    parser.add_argument('-l', '--lines', type=int, default=3, help='Number of context lines')
    parser.add_argument('fromdir', help='First directory path')
    parser.add_argument('todir', help='Second directory path')
    options = parser.parse_args()

    from_files = collect_files(options.fromdir)
    to_files = collect_files(options.todir)

    all_keys = sorted(set(from_files) | set(to_files))
    for rel_path in all_keys:
        from_path = from_files.get(rel_path)
        to_path = to_files.get(rel_path)

        print(f"\n=== Comparing: {rel_path} ===")
        if from_path and to_path:
            diff = compare_files(from_path, to_path, options)
            if options.m:
                print(diff[0])
            else:
                sys.stdout.writelines(diff)
        elif from_path:
            print(f"Only in {options.fromdir}: {rel_path}")
        elif to_path:
            print(f"Only in {options.todir}: {rel_path}")

if __name__ == '__main__':
    main()
