#!/usr/bin/env python3
import sys
import os
import difflib
import argparse
from datetime import datetime, timezone
from pathlib import Path


def color_diff(diff_lines):
    """Apply color formatting to diff lines."""
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
    """Get formatted modification time of a file."""
    t = datetime.fromtimestamp(os.stat(path).st_mtime, timezone.utc)
    return t.astimezone().isoformat()


def file_size(path):
    """Get file size in bytes."""
    return os.stat(path).st_size


def collect_files(root_dir):
    """Collect all files in a directory tree with normalized paths."""
    files = {}
    for dirpath, _, filenames in os.walk(root_dir):
        for f in filenames:
            full_path = os.path.join(dirpath, f)
            # Use normalized relative path: lowercase, forward slashes
            rel_path = os.path.relpath(full_path, root_dir)
            normalized_path = os.path.normcase(rel_path).replace("\\", "/")
            files[normalized_path] = full_path
    return files


def get_diff_stats(file1, file2):
    """Calculate diff statistics between two files."""
    try:
        with open(file1, 'r', encoding='utf-8', errors='ignore') as f1:
            lines1 = f1.readlines()
        with open(file2, 'r', encoding='utf-8', errors='ignore') as f2:
            lines2 = f2.readlines()
        
        diff = list(difflib.unified_diff(lines1, lines2, lineterm=''))
        
        additions = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
        deletions = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))
        
        return {
            'additions': additions,
            'deletions': deletions,
            'total_changes': additions + deletions,
            'lines1': len(lines1),
            'lines2': len(lines2)
        }
    except Exception as e:
        return {
            'additions': '?',
            'deletions': '?',
            'total_changes': '?',
            'lines1': '?',
            'lines2': '?',
            'error': str(e)
        }


def strip_ansi_codes(text):
    """Remove ANSI color codes from text."""
    import re
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


def print_side_by_side_diff(file1, file2, rel_path, terminal_width=160, output_file=None):
    """Print side-by-side diff in the requested format."""
    try:
        with open(file1, 'r', encoding='utf-8', errors='ignore') as f1:
            lines1 = f1.readlines()
        with open(file2, 'r', encoding='utf-8', errors='ignore') as f2:
            lines2 = f2.readlines()
    except Exception as e:
        print(f"Error reading files: {e}")
        return
    
    # Check if files are identical
    if lines1 == lines2:
        return  # Skip identical files
    
    # Calculate column width (split terminal width in half, minus separator)
    col_width = (terminal_width - 3) // 2  # 3 chars for " | "
    
    def output_line(line):
        """Output line to console and/or file."""
        if output_file:
            # Strip ANSI codes when writing to file
            clean_line = strip_ansi_codes(line)
            output_file.write(clean_line + '\n')
        else:
            print(line)
    
    output_line(f"Comparing: {rel_path}")
    output_line("-" * terminal_width)
    
    # Print header
    left_header = "LEFT".center(col_width)
    right_header = "RIGHT".center(col_width)
    output_line(f"{left_header} | {right_header}")
    output_line("-" * terminal_width)
    
    # Use difflib to get side-by-side comparison
    differ = difflib.unified_diff(lines1, lines2, lineterm='')
    diff_lines = list(differ)
    
    # If no diff lines, files might be identical
    if not diff_lines:
        return
    
    # Create side-by-side view
    max_lines = max(len(lines1), len(lines2))
    
    # Pad shorter file with empty lines
    while len(lines1) < max_lines:
        lines1.append('')
    while len(lines2) < max_lines:
        lines2.append('')
    
    # Print side by side
    for i in range(max_lines):
        left_line = lines1[i].rstrip('\n') if i < len(lines1) else ''
        right_line = lines2[i].rstrip('\n') if i < len(lines2) else ''
        
        # Truncate lines if too long
        if len(left_line) > col_width:
            left_line = left_line[:col_width-3] + '...'
        if len(right_line) > col_width:
            right_line = right_line[:col_width-3] + '...'
        
        # Pad lines to column width
        left_line = left_line.ljust(col_width)
        right_line = right_line.ljust(col_width)
        
        # Color coding based on differences
        if lines1[i] != lines2[i]:
            if not lines1[i].strip():  # Left is empty (addition)
                if output_file:
                    output_line(f"{left_line} | {right_line}")
                else:
                    print(f"{left_line} | \033[32m{right_line}\033[0m")
            elif not lines2[i].strip():  # Right is empty (deletion)
                if output_file:
                    output_line(f"{left_line} | {right_line}")
                else:
                    print(f"\033[31m{left_line}\033[0m | {right_line}")
            else:  # Both have content but different (modification)
                if output_file:
                    output_line(f"{left_line} | {right_line}")
                else:
                    print(f"\033[33m{left_line}\033[0m | \033[33m{right_line}\033[0m")
        else:
            output_line(f"{left_line} | {right_line}")
    
    output_line("-" * terminal_width)


def print_report_header(fromdir, todir, output_file=None):
    """Print the report header in the requested format."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def output_line(line):
        """Output line to console and/or file."""
        if output_file:
            output_file.write(line + '\n')
        else:
            print(line)
    
    output_line("=" * 160)
    output_line("Folder Comparison Report")
    output_line(f"Generated: {now}")
    output_line(f"Left: {fromdir}")
    output_line(f"Right: {todir}")
    output_line("=" * 160)


def print_subdirectory_section(rel_path, different_files, output_file=None):
    """Print subdirectory section header."""
    def output_line(line):
        """Output line to console and/or file."""
        if output_file:
            output_file.write(line + '\n')
        else:
            print(line)
    
    if rel_path == '.':
        subdir_name = "Root directory"
    else:
        subdir_name = rel_path
    
    output_line(f"\nSubdirectory: {subdir_name}")
    output_line("")
    if different_files:
        output_line("  Different files:")
    else:
        output_line("  No different files found.")


def print_tabular_summary(from_files, to_files, fromdir, todir):
    """Print a tabular summary of all file differences."""
    print(f"\n{'='*80}")
    print(f"DIRECTORY COMPARISON SUMMARY")
    print(f"{'='*80}")
    print(f"From: {fromdir}")
    print(f"To:   {todir}")
    print(f"{'='*80}")
    
    # Header
    header = f"{'File':<40} {'Status':<12} {'Size 1':<10} {'Size 2':<10} {'+/-':<8} {'Changes':<8}"
    print(header)
    print('-' * len(header))
    
    all_keys = sorted(set(from_files) | set(to_files))
    
    stats = {
        'total_files': len(all_keys),
        'modified': 0,
        'added': 0,
        'removed': 0,
        'identical': 0,
        'total_additions': 0,
        'total_deletions': 0
    }
    
    for rel_path in all_keys:
        from_path = from_files.get(rel_path)
        to_path = to_files.get(rel_path)
        
        # Truncate filename if too long
        display_path = rel_path[:37] + '...' if len(rel_path) > 40 else rel_path
        
        if from_path and to_path:
            # Both files exist - check if they're different
            try:
                with open(from_path, 'rb') as f1, open(to_path, 'rb') as f2:
                    if f1.read() == f2.read():
                        status = "IDENTICAL"
                        size1 = file_size(from_path)
                        size2 = file_size(to_path)
                        changes = "0"
                        diff_info = ""
                        stats['identical'] += 1
                    else:
                        status = "MODIFIED"
                        size1 = file_size(from_path)
                        size2 = file_size(to_path)
                        diff_stats = get_diff_stats(from_path, to_path)
                        if isinstance(diff_stats['additions'], int):
                            changes = f"{diff_stats['total_changes']}"
                            diff_info = f"+{diff_stats['additions']}/-{diff_stats['deletions']}"
                            stats['total_additions'] += diff_stats['additions']
                            stats['total_deletions'] += diff_stats['deletions']
                        else:
                            changes = "?"
                            diff_info = "?/?"
                        stats['modified'] += 1
            except Exception:
                status = "ERROR"
                size1 = "?"
                size2 = "?"
                changes = "?"
                diff_info = "?/?"
                
        elif from_path:
            status = "REMOVED"
            size1 = file_size(from_path)
            size2 = "-"
            changes = "?"
            diff_info = ""
            stats['removed'] += 1
        else:
            status = "ADDED"
            size1 = "-"
            size2 = file_size(to_path)
            changes = "?"
            diff_info = ""
            stats['added'] += 1
        
        # Format sizes
        size1_str = f"{size1:,}" if isinstance(size1, int) else str(size1)
        size2_str = f"{size2:,}" if isinstance(size2, int) else str(size2)
        
        print(f"{display_path:<40} {status:<12} {size1_str:<10} {size2_str:<10} {diff_info:<8} {changes:<8}")
    
    # Print summary statistics
    print('-' * len(header))
    print(f"\nSUMMARY:")
    print(f"  Total files: {stats['total_files']}")
    print(f"  Modified:    {stats['modified']}")
    print(f"  Added:       {stats['added']}")
    print(f"  Removed:     {stats['removed']}")
    print(f"  Identical:   {stats['identical']}")
    if stats['total_additions'] or stats['total_deletions']:
        print(f"  Total changes: +{stats['total_additions']}/-{stats['total_deletions']}")


def compare_files(file1, file2, options):
    """Compare two files and return diff output."""
    fromdate = file_mtime(file1)
    todate = file_mtime(file2)
    
    try:
        with open(file1, 'r', encoding='utf-8', errors='ignore') as ff:
            fromlines = ff.readlines()
        with open(file2, 'r', encoding='utf-8', errors='ignore') as tf:
            tolines = tf.readlines()
    except Exception as e:
        return [f"Error reading files: {e}"]

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
    parser = argparse.ArgumentParser(
        description='Compare two directories and show differences',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s dir1 dir2                    # Show context diff for all files
  %(prog)s -r dir1 dir2                 # Show side-by-side report format
  %(prog)s -t dir1 dir2                 # Show tabular summary only
  %(prog)s -u dir1 dir2                 # Show unified diff format
  %(prog)s -m dir1 dir2                 # Generate HTML side-by-side diff
        """)
    
    parser.add_argument('-c', action='store_true', help='Context format diff (default)')
    parser.add_argument('-u', action='store_true', help='Unified format diff')
    parser.add_argument('-m', action='store_true', help='HTML side-by-side diff')
    parser.add_argument('-n', action='store_true', help='Ndiff format diff')
    parser.add_argument('-r', '--report', action='store_true', help='Show side-by-side report format')
    parser.add_argument('-t', '--table', action='store_true', help='Show tabular summary')
    parser.add_argument('-s', '--summary-only', action='store_true', help='Show only tabular summary (no individual diffs)')
    parser.add_argument('-l', '--lines', type=int, default=3, help='Number of context lines (default: 3)')
    parser.add_argument('--no-color', action='store_true', help='Disable colored output')
    parser.add_argument('--width', type=int, default=160, help='Terminal width for side-by-side display (default: 160)')
    parser.add_argument('-o', '--output', type=str, help='Output to file (automatically removes ANSI colors)')
    parser.add_argument('fromdir', help='First directory path')
    parser.add_argument('todir', help='Second directory path')
    
    options = parser.parse_args()

    # Validate directories
    if not os.path.isdir(options.fromdir):
        print(f"Error: '{options.fromdir}' is not a directory", file=sys.stderr)
        sys.exit(1)
    if not os.path.isdir(options.todir):
        print(f"Error: '{options.todir}' is not a directory", file=sys.stderr)
        sys.exit(1)

    from_files = collect_files(options.fromdir)
    to_files = collect_files(options.todir)

    # Setup output file if specified
    output_file = None
    if options.output:
        try:
            output_file = open(options.output, 'w', encoding='utf-8')
            print(f"Writing output to: {options.output}")
        except Exception as e:
            print(f"Error opening output file: {e}", file=sys.stderr)
            sys.exit(1)

    try:

    # Show report format if requested
    if options.report:
        print_report_header(options.fromdir, options.todir)
        
        # Group files by subdirectory
        subdirs = {}
        all_keys = sorted(set(from_files) | set(to_files))
        
        for rel_path in all_keys:
            from_path = from_files.get(rel_path)
            to_path = to_files.get(rel_path)
            
            # Get subdirectory
            subdir = os.path.dirname(rel_path) if os.path.dirname(rel_path) else '.'
            if subdir not in subdirs:
                subdirs[subdir] = []
            
            # Only include files that are different
            if from_path and to_path:
                try:
                    with open(from_path, 'rb') as f1, open(to_path, 'rb') as f2:
                        if f1.read() != f2.read():
                            subdirs[subdir].append(rel_path)
                except Exception:
                    subdirs[subdir].append(rel_path)
            elif from_path or to_path:  # File only exists in one directory
                subdirs[subdir].append(rel_path)
        
        # Print each subdirectory
        for subdir in sorted(subdirs.keys()):
            different_files = subdirs[subdir]
            print_subdirectory_section(subdir, different_files)
            
            for rel_path in different_files:
                from_path = from_files.get(rel_path)
                to_path = to_files.get(rel_path)
                
                if from_path and to_path:
                    print()
                    print_side_by_side_diff(from_path, to_path, rel_path, options.width)
                elif from_path:
                    print(f"Only in {options.fromdir}: {rel_path}")
                elif to_path:
                    print(f"Only in {options.todir}: {rel_path}")
        
        return

    # Show tabular summary if requested
    if options.table or options.summary_only:
        print_tabular_summary(from_files, to_files, options.fromdir, options.todir)
        
        if options.summary_only:
            return

    # Show individual file diffs unless summary-only mode
    if not options.summary_only:
        all_keys = sorted(set(from_files) | set(to_files))
        files_processed = 0
        
        for rel_path in all_keys:
            from_path = from_files.get(rel_path)
            to_path = to_files.get(rel_path)

            if not options.table:  # Don't repeat header if table already shown
                print(f"\n{'='*60}")
                print(f"Comparing: {rel_path}")
                print(f"{'='*60}")
            
            if from_path and to_path:
                if not options.table:
                    print(f"From: {from_path}")
                    print(f"To:   {to_path}")
                
                # Check if files are identical
                try:
                    with open(from_path, 'rb') as f1, open(to_path, 'rb') as f2:
                        if f1.read() == f2.read():
                            if not options.table:
                                print("Files are identical.")
                            continue
                except Exception as e:
                    print(f"Error comparing files: {e}")
                    continue
                
                diff = compare_files(from_path, to_path, options)
                if options.m:
                    print(diff[0])
                else:
                    diff_lines = list(diff)
                    if diff_lines:
                        if options.no_color:
                            # Strip color codes
                            for line in diff_lines:
                                clean_line = line.replace('\033[32m', '').replace('\033[31m', '').replace('\033[33m', '').replace('\033[0m', '')
                                print(clean_line, end='')
                        else:
                            for line in diff_lines:
                                print(line, end='')
                    else:
                        if not options.table:
                            print("Files are identical.")
                files_processed += 1
                
            elif from_path:
                if not options.table:
                    print(f"Only in {options.fromdir}: {rel_path}")
            elif to_path:
                if not options.table:
                    print(f"Only in {options.todir}: {rel_path}")


if __name__ == '__main__':
    main()
