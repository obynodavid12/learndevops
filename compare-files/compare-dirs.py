import os
import sys
import argparse
import filecmp
import difflib
from colorama import Fore, Style, init

init(autoreset=True)

def side_by_side_diff(left_lines, right_lines, width=100, color=True, file=None):
    max_lines = max(len(left_lines), len(right_lines))
    left_lines += [''] * (max_lines - len(left_lines))
    right_lines += [''] * (max_lines - len(right_lines))

    header = f"{'LEFT'.ljust(width)} | {'DIFF':^5} | {'RIGHT'.ljust(width)}"
    separator = f"{'-'*width}-+-----+-{'-'*width}"

    if file:
        print(header, file=file)
        print(separator, file=file)
    print(header)
    print(separator)

    for l, r in zip(left_lines, right_lines):
        l_str, r_str = l.rstrip(), r.rstrip()
        if l_str == r_str:
            diff = " "
            l_out = l_str
            r_out = r_str
        elif l_str and not r_str:
            diff = "-"
            l_out = Fore.RED + l_str + Style.RESET_ALL if color else l_str
            r_out = ""
        elif not l_str and r_str:
            diff = "+"
            l_out = ""
            r_out = Fore.GREEN + r_str + Style.RESET_ALL if color else r_str
        else:
            diff = "|"
            l_out = Fore.YELLOW + l_str + Style.RESET_ALL if color else l_str
            r_out = Fore.GREEN + r_str + Style.RESET_ALL if color else r_str

        line_col = f"{l_out.ljust(width)} |  {diff}  | {r_out.ljust(width)}"
        line_plain = f"{l_str.ljust(width)} |  {diff}  | {r_str.ljust(width)}"
        print(line_col)
        if file:
            print(line_plain, file=file)

def compare_files(left_file, right_file, width=100, file=None):
    try:
        with open(left_file, encoding='utf-8', errors='replace') as lf:
            left_lines = lf.readlines()
    except Exception as e:
        left_lines = [f"[Could not read: {e}]"]

    try:
        with open(right_file, encoding='utf-8', errors='replace') as rf:
            right_lines = rf.readlines()
    except Exception as e:
        right_lines = [f"[Could not read: {e}]"]

    side_by_side_diff(left_lines, right_lines, width=width, color=True, file=file)

def walk_and_compare(left_dir, right_dir, width=100, file=None):
    dcmp = filecmp.dircmp(left_dir, right_dir)
    # Only in left
    for name in dcmp.left_only:
        line = f"[Only in LEFT] {os.path.join(left_dir, name)}"
        print(Fore.YELLOW + line + Style.RESET_ALL)
        if file:
            print(line, file=file)
    # Only in right
    for name in dcmp.right_only:
        line = f"[Only in RIGHT] {os.path.join(right_dir, name)}"
        print(Fore.CYAN + line + Style.RESET_ALL)
        if file:
            print(line, file=file)
    # Different files
    for name in dcmp.diff_files:
        left_file = os.path.join(left_dir, name)
        right_file = os.path.join(right_dir, name)
        header = f"\n=== {name} differs ==="
        print(Fore.MAGENTA + header + Style.RESET_ALL)
        if file:
            print(header, file=file)
        compare_files(left_file, right_file, width=width, file=file)
    # Recurse into subdirectories
    for subdir in dcmp.subdirs:
        subdir_header = f"\n>>> Entering subdirectory: {subdir}\n"
        print(Fore.BLUE + subdir_header + Style.RESET_ALL)
        if file:
            print(subdir_header, file=file)
        walk_and_compare(
            os.path.join(left_dir, subdir),
            os.path.join(right_dir, subdir),
            width=width,
            file=file
        )

def main():
    parser = argparse.ArgumentParser(description="Compare two directories and print colored side-by-side diffs with a difference column. Optionally output to a text file.")
    parser.add_argument("left", help="First directory path")
    parser.add_argument("right", help="Second directory path")
    parser.add_argument("--width", type=int, default=100, help="Column width for table display (default: 100)")
    parser.add_argument("--output", help="Output text file for the report")
    args = parser.parse_args()

    if not os.path.isdir(args.left) or not os.path.isdir(args.right):
        print(f"{Fore.RED}ERROR: Both arguments must be directories.{Style.RESET_ALL}")
        sys.exit(1)

    print(f"Comparing directories: {args.left} <=> {args.right}\n")
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            walk_and_compare(args.left, args.right, width=args.width, file=f)
    walk_and_compare(args.left, args.right, width=args.width, file=None)

if __name__ == "__main__":
    main()
