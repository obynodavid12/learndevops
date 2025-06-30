import os
import sys
import filecmp
import difflib
import csv
import argparse
import datetime
from pathlib import Path
from typing import List, Dict, Tuple

# ANSI color codes for terminal output
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

class DiffReporter:
    def __init__(self, path1: str, path2: str):
        self.path1 = path1
        self.path2 = path2
        self.report_data = {
            'left_only': [],
            'right_only': [],
            'diff_files': [],
            'identical_files': [],
            'subdirs': []
        }
        self.file_diffs = {}
        
    def analyze_directories(self):
        """Analyze directories and collect diff data"""
        dcmp = filecmp.dircmp(self.path1, self.path2)
        self._collect_diff_data(dcmp, "")
        
    def _collect_diff_data(self, dcmp, rel_path: str):
        """Recursively collect diff data"""
        current_path = rel_path
        
        # Files only in left directory
        for name in dcmp.left_only:
            self.report_data['left_only'].append({
                'path': os.path.join(current_path, name),
                'full_path': os.path.join(dcmp.left, name),
                'type': 'directory' if os.path.isdir(os.path.join(dcmp.left, name)) else 'file'
            })
            
        # Files only in right directory
        for name in dcmp.right_only:
            self.report_data['right_only'].append({
                'path': os.path.join(current_path, name),
                'full_path': os.path.join(dcmp.right, name),
                'type': 'directory' if os.path.isdir(os.path.join(dcmp.right, name)) else 'file'
            })
            
        # Different files
        for name in dcmp.diff_files:
            file_path = os.path.join(current_path, name)
            self.report_data['diff_files'].append({
                'path': file_path,
                'left_path': os.path.join(dcmp.left, name),
                'right_path': os.path.join(dcmp.right, name)
            })
            
            # Get detailed diff for the file
            self.file_diffs[file_path] = self._get_file_diff(
                os.path.join(dcmp.left, name),
                os.path.join(dcmp.right, name)
            )
            
        # Identical files
        for name in dcmp.same_files:
            self.report_data['identical_files'].append({
                'path': os.path.join(current_path, name)
            })
            
        # Process subdirectories
        for name, sub_dcmp in dcmp.subdirs.items():
            sub_path = os.path.join(current_path, name) if current_path else name
            self.report_data['subdirs'].append(sub_path)
            self._collect_diff_data(sub_dcmp, sub_path)
            
    def _get_file_diff(self, file1: str, file2: str) -> List[str]:
        """Get unified diff for two files"""
        try:
            with open(file1, 'r', encoding='utf-8', errors='ignore') as f1, \
                 open(file2, 'r', encoding='utf-8', errors='ignore') as f2:
                f1_lines = f1.readlines()
                f2_lines = f2.readlines()
                
                diff = list(difflib.unified_diff(
                    f1_lines, f2_lines,
                    fromfile=file1, tofile=file2,
                    lineterm=''
                ))
                return diff
        except Exception as e:
            return [f"Error reading files: {str(e)}"]

    def _get_diff_summary(self, diff_lines: List[str]) -> Dict[str, int]:
        """Get summary statistics from diff lines"""
        summary = {'additions': 0, 'deletions': 0, 'context': 0}
        for line in diff_lines:
            if line.startswith('+') and not line.startswith('+++'):
                summary['additions'] += 1
            elif line.startswith('-') and not line.startswith('---'):
                summary['deletions'] += 1
            elif not line.startswith('@@') and not line.startswith('+++') and not line.startswith('---'):
                summary['context'] += 1
        return summary

    def print_table_report(self):
        """Print report in table format"""
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*100}")
        print(f"DIRECTORY COMPARISON REPORT - TABLE FORMAT")
        print(f"{'='*100}{Colors.END}")
        print(f"{Colors.BOLD}Path 1:{Colors.END} {self.path1}")
        print(f"{Colors.BOLD}Path 2:{Colors.END} {self.path2}")
        print(f"{Colors.BOLD}Generated:{Colors.END} {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # Summary table
        print(f"{Colors.BOLD}{Colors.YELLOW}SUMMARY TABLE{Colors.END}")
        print(f"{'Status':<20} {'Count':<10}")
        print("-" * 30)
        print(f"{'Only in Path 1':<20} {Colors.RED}{len(self.report_data['left_only']):<10}{Colors.END}")
        print(f"{'Only in Path 2':<20} {Colors.GREEN}{len(self.report_data['right_only']):<10}{Colors.END}")
        print(f"{'Different Files':<20} {Colors.YELLOW}{len(self.report_data['diff_files']):<10}{Colors.END}")
        print(f"{'Identical Files':<20} {Colors.CYAN}{len(self.report_data['identical_files']):<10}{Colors.END}")
        print()

        # Detailed table
        print(f"{Colors.BOLD}DETAILED FILE COMPARISON TABLE{Colors.END}")
        print(f"{'Status':<15} {'Type':<10} {'Path':<50} {'Details':<30}")
        print("-" * 105)

        # Files only in left
        for item in self.report_data['left_only']:
            status = f"{Colors.RED}Only in Path 1{Colors.END}"
            type_str = "📁 DIR" if item['type'] == 'directory' else "📄 FILE"
            print(f"{status:<24} {type_str:<10} {item['path']:<50} {'-':<30}")

        # Files only in right
        for item in self.report_data['right_only']:
            status = f"{Colors.GREEN}Only in Path 2{Colors.END}"
            type_str = "📁 DIR" if item['type'] == 'directory' else "📄 FILE"
            print(f"{status:<24} {type_str:<10} {item['path']:<50} {'-':<30}")

        # Different files
        for item in self.report_data['diff_files']:
            status = f"{Colors.YELLOW}Different{Colors.END}"
            type_str = "📄 FILE"
            details = ""
            if item['path'] in self.file_diffs:
                diff_summary = self._get_diff_summary(self.file_diffs[item['path']])
                details = f"+{diff_summary['additions']} -{diff_summary['deletions']}"
            print(f"{status:<24} {type_str:<10} {item['path']:<50} {details:<30}")

        # Identical files
        for item in self.report_data['identical_files']:
            status = f"{Colors.CYAN}Identical{Colors.END}"
            type_str = "📄 FILE"
            print(f"{status:<24} {type_str:<10} {item['path']:<50} {'Same content':<30}")

        print()

    def _generate_side_by_side_diff(self, file1: str, file2: str, max_width: int = 60) -> List[str]:
        """Generate side-by-side diff comparison"""
        try:
            with open(file1, 'r', encoding='utf-8', errors='ignore') as f1, \
                 open(file2, 'r', encoding='utf-8', errors='ignore') as f2:
                f1_lines = [line.rstrip('\n') for line in f1.readlines()]
                f2_lines = [line.rstrip('\n') for line in f2.readlines()]
        except Exception as e:
            return [f"Error reading files: {str(e)}"]

        # Create side-by-side comparison
        result = []
        max_lines = max(len(f1_lines), len(f2_lines))
        
        for i in range(max_lines):
            left_line = f1_lines[i] if i < len(f1_lines) else ""
            right_line = f2_lines[i] if i < len(f2_lines) else ""
            
            # Truncate lines if too long
            if len(left_line) > max_width:
                left_line = left_line[:max_width-3] + "..."
            if len(right_line) > max_width:
                right_line = right_line[:max_width-3] + "..."
            
            # Format the comparison line
            left_formatted = f"{left_line:<{max_width}}"
            right_formatted = f"{right_line:<{max_width}}"
            
            # Add markers for different lines
            marker = " | " if left_line == right_line else " | "
            result.append(f"{left_formatted}{marker}{right_formatted}")
        
        return result

    def save_tabular_diff_report(self, filename: str):
        """Save side-by-side tabular diff report to text file"""
        with open(filename, 'w', encoding='utf-8') as f:
            # Header
            f.write("="*150 + "\n")
            f.write("Folder Comparison Report\n")
            f.write(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Left: {self.path1}\n")
            f.write(f"Right: {self.path2}\n")
            f.write("="*150 + "\n\n")
            
            # Process each subdirectory
            processed_subdirs = set()
            
            # Group files by their directory
            files_by_dir = {}
            
            # Add different files to their respective directories
            for item in self.report_data['diff_files']:
                dir_path = os.path.dirname(item['path'])
                if dir_path == '':
                    dir_path = '.'
                if dir_path not in files_by_dir:
                    files_by_dir[dir_path] = {'diff': [], 'left_only': [], 'right_only': []}
                files_by_dir[dir_path]['diff'].append(item)
            
            # Add files only in left
            for item in self.report_data['left_only']:
                if item['type'] == 'file':
                    dir_path = os.path.dirname(item['path'])
                    if dir_path == '':
                        dir_path = '.'
                    if dir_path not in files_by_dir:
                        files_by_dir[dir_path] = {'diff': [], 'left_only': [], 'right_only': []}
                    files_by_dir[dir_path]['left_only'].append(item)
            
            # Add files only in right
            for item in self.report_data['right_only']:
                if item['type'] == 'file':
                    dir_path = os.path.dirname(item['path'])
                    if dir_path == '':
                        dir_path = '.'
                    if dir_path not in files_by_dir:
                        files_by_dir[dir_path] = {'diff': [], 'left_only': [], 'right_only': []}
                    files_by_dir[dir_path]['right_only'].append(item)
            
            # Process each directory
            for dir_path, files in files_by_dir.items():
                if not files['diff'] and not files['left_only'] and not files['right_only']:
                    continue
                    
                f.write(f"Subdirectory: {dir_path}\n\n")
                
                # Show files only in one side
                if files['left_only']:
                    f.write("  Files only in LEFT:\n")
                    for item in files['left_only']:
                        f.write(f"    - {os.path.basename(item['path'])}\n")
                    f.write("\n")
                
                if files['right_only']:
                    f.write("  Files only in RIGHT:\n")
                    for item in files['right_only']:
                        f.write(f"    + {os.path.basename(item['path'])}\n")
                    f.write("\n")
                
                # Show different files with side-by-side comparison
                if files['diff']:
                    f.write("  Different files:\n\n")
                    
                    for item in files['diff']:
                        filename = os.path.basename(item['path'])
                        f.write(f"Comparing: {filename} vs {filename}\n")
                        f.write("-" * 150 + "\n")
                        
                        # Create column headers
                        left_header = f"{'LEFT':<60}"
                        right_header = f"{'RIGHT':<60}"
                        f.write(f"{left_header} | {right_header}\n")
                        f.write("-" * 150 + "\n")
                        
                        # Generate side-by-side diff
                        side_by_side = self._generate_side_by_side_diff(item['left_path'], item['right_path'])
                        
                        for line in side_by_side:
                            f.write(f"{line}\n")
                        
                        f.write("-" * 150 + "\n\n")
                
                f.write("\n")
        
        print(f"Tabular diff report saved to: {filename}")

    def print_colored_report(self):
        """Print colored report to terminal"""
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}")
        print(f"DIRECTORY COMPARISON REPORT")
        print(f"{'='*80}{Colors.END}")
        print(f"{Colors.BOLD}Path 1:{Colors.END} {self.path1}")
        print(f"{Colors.BOLD}Path 2:{Colors.END} {self.path2}")
        print(f"{Colors.BOLD}Generated:{Colors.END} {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Summary
        print(f"{Colors.BOLD}{Colors.YELLOW}SUMMARY{Colors.END}")
        print(f"Files only in Path 1: {Colors.RED}{len(self.report_data['left_only'])}{Colors.END}")
        print(f"Files only in Path 2: {Colors.GREEN}{len(self.report_data['right_only'])}{Colors.END}")
        print(f"Different files: {Colors.YELLOW}{len(self.report_data['diff_files'])}{Colors.END}")
        print(f"Identical files: {Colors.CYAN}{len(self.report_data['identical_files'])}{Colors.END}")
        print()
        
        # Files only in left
        if self.report_data['left_only']:
            print(f"{Colors.BOLD}{Colors.RED}FILES ONLY IN PATH 1:{Colors.END}")
            for item in self.report_data['left_only']:
                icon = "📁" if item['type'] == 'directory' else "📄"
                print(f"  {Colors.RED}-{Colors.END} {icon} {item['path']}")
            print()
            
        # Files only in right
        if self.report_data['right_only']:
            print(f"{Colors.BOLD}{Colors.GREEN}FILES ONLY IN PATH 2:{Colors.END}")
            for item in self.report_data['right_only']:
                icon = "📁" if item['type'] == 'directory' else "📄"
                print(f"  {Colors.GREEN}+{Colors.END} {icon} {item['path']}")
            print()
            
        # Different files
        if self.report_data['diff_files']:
            print(f"{Colors.BOLD}{Colors.YELLOW}DIFFERENT FILES:{Colors.END}")
            for item in self.report_data['diff_files']:
                print(f"  {Colors.YELLOW}≠{Colors.END} 📄 {item['path']}")
                
                # Show diff preview (first few lines)
                if item['path'] in self.file_diffs:
                    diff_lines = self.file_diffs[item['path']][:10]  # First 10 lines
                    for line in diff_lines:
                        if line.startswith('+++') or line.startswith('---'):
                            print(f"    {Colors.BLUE}{line}{Colors.END}")
                        elif line.startswith('@@'):
                            print(f"    {Colors.MAGENTA}{line}{Colors.END}")
                        elif line.startswith('+'):
                            print(f"    {Colors.GREEN}{line}{Colors.END}")
                        elif line.startswith('-'):
                            print(f"    {Colors.RED}{line}{Colors.END}")
                        else:
                            print(f"    {line}")
                    if len(self.file_diffs[item['path']]) > 10:
                        print(f"    {Colors.CYAN}... (truncated, see full report for complete diff){Colors.END}")
                print()
    
    def save_csv_report(self, filename: str):
        """Save report as CSV file with detailed differences"""
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Header
            writer.writerow(['Type', 'Status', 'Path', 'File_Type', 'Details', 'Additions', 'Deletions', 'Diff_Content'])
            
            # Write data for files only in left
            for item in self.report_data['left_only']:
                writer.writerow(['File/Dir', 'Only in Path 1', item['path'], item['type'], f"Only exists in {self.path1}", '', '', ''])
                
            # Write data for files only in right
            for item in self.report_data['right_only']:
                writer.writerow(['File/Dir', 'Only in Path 2', item['path'], item['type'], f"Only exists in {self.path2}", '', '', ''])
                
            # Write data for different files with detailed diff
            for item in self.report_data['diff_files']:
                if item['path'] in self.file_diffs:
                    diff_lines = self.file_diffs[item['path']]
                    diff_summary = self._get_diff_summary(diff_lines)
                    
                    # Create a clean diff content for CSV (remove ANSI codes and format nicely)
                    diff_content = []
                    for line in diff_lines[:50]:  # Limit to first 50 lines for CSV readability
                        if line.startswith('+++') or line.startswith('---'):
                            diff_content.append(f"FILE: {line}")
                        elif line.startswith('@@'):
                            diff_content.append(f"SECTION: {line}")
                        elif line.startswith('+') and not line.startswith('+++'):
                            diff_content.append(f"ADDED: {line[1:]}")
                        elif line.startswith('-') and not line.startswith('---'):
                            diff_content.append(f"REMOVED: {line[1:]}")
                        elif line.strip():  # Only include non-empty context lines
                            diff_content.append(f"CONTEXT: {line}")
                    
                    diff_text = '\n'.join(diff_content)
                    if len(self.file_diffs[item['path']]) > 50:
                        diff_text += '\n... (truncated - see full diff in HTML report)'
                    
                    writer.writerow([
                        'File', 
                        'Different', 
                        item['path'], 
                        'file',
                        f"Content differs: +{diff_summary['additions']} -{diff_summary['deletions']}", 
                        diff_summary['additions'],
                        diff_summary['deletions'],
                        diff_text
                    ])
                else:
                    writer.writerow(['File', 'Different', item['path'], 'file', 'Content differs (could not read diff)', '', '', 'Error reading file diff'])
                
            # Write data for identical files
            for item in self.report_data['identical_files']:
                writer.writerow(['File', 'Identical', item['path'], 'file', 'Same content', '', '', ''])
        
        print(f"Enhanced CSV report saved to: {filename}")
    
    def save_html_report(self, filename: str):
        """Save report as HTML file"""
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Directory Comparison Report</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }}
        h1, h2 {{
            color: #333;
            border-bottom: 2px solid #007acc;
            padding-bottom: 10px;
        }}
        .header {{
            background: linear-gradient(135deg, #007acc, #0056b3);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .summary-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            border-left: 4px solid;
        }}
        .left-only {{ border-left-color: #dc3545; }}
        .right-only {{ border-left-color: #28a745; }}
        .different {{ border-left-color: #ffc107; }}
        .identical {{ border-left-color: #17a2b8; }}
        .file-list {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }}
        .file-item {{
            padding: 10px;
            margin: 5px 0;
            border-radius: 5px;
            display: flex;
            align-items: center;
        }}
        .file-item.left-only {{ background: #f8d7da; color: #721c24; }}
        .file-item.right-only {{ background: #d4edda; color: #155724; }}
        .file-item.different {{ background: #fff3cd; color: #856404; }}
        .icon {{ margin-right: 10px; font-size: 16px; }}
        .diff-content {{
            background: #2d3748;
            color: #e2e8f0;
            padding: 15px;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            overflow-x: auto;
            margin-top: 10px;
        }}
        .diff-add {{ color: #68d391; }}
        .diff-remove {{ color: #fc8181; }}
        .diff-info {{ color: #63b3ed; }}
        .diff-hunk {{ color: #d6bcfa; }}
        .collapsible {{
            cursor: pointer;
            padding: 10px;
            background: #e9ecef;
            border: none;
            text-align: left;
            width: 100%;
            border-radius: 5px;
            margin: 5px 0;
        }}
        .collapsible:hover {{ background: #dee2e6; }}
        .content {{
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.2s ease-out;
        }}
        .content.active {{ max-height: 1000px; }}
        .diff-stats {{
            background: #e9ecef;
            padding: 5px 10px;
            border-radius: 3px;
            font-size: 12px;
            margin-left: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Directory Comparison Report</h1>
            <p><strong>Path 1:</strong> {self.path1}</p>
            <p><strong>Path 2:</strong> {self.path2}</p>
            <p><strong>Generated:</strong> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="summary">
            <div class="summary-card left-only">
                <h3>{len(self.report_data['left_only'])}</h3>
                <p>Only in Path 1</p>
            </div>
            <div class="summary-card right-only">
                <h3>{len(self.report_data['right_only'])}</h3>
                <p>Only in Path 2</p>
            </div>
            <div class="summary-card different">
                <h3>{len(self.report_data['diff_files'])}</h3>
                <p>Different Files</p>
            </div>
            <div class="summary-card identical">
                <h3>{len(self.report_data['identical_files'])}</h3>
                <p>Identical Files</p>
            </div>
        </div>
"""
        
        # Files only in left
        if self.report_data['left_only']:
            html_content += """
        <h2>🔴 Files Only in Path 1</h2>
        <div class="file-list">
"""
            for item in self.report_data['left_only']:
                icon = "📁" if item['type'] == 'directory' else "📄"
                html_content += f'            <div class="file-item left-only"><span class="icon">{icon}</span>{item["path"]}</div>\n'
            html_content += "        </div>\n"
        
        # Files only in right
        if self.report_data['right_only']:
            html_content += """
        <h2>🟢 Files Only in Path 2</h2>
        <div class="file-list">
"""
            for item in self.report_data['right_only']:
                icon = "📁" if item['type'] == 'directory' else "📄"
                html_content += f'            <div class="file-item right-only"><span class="icon">{icon}</span>{item["path"]}</div>\n'
            html_content += "        </div>\n"
        
        # Different files
        if self.report_data['diff_files']:
            html_content += """
        <h2>🟡 Different Files</h2>
        <div class="file-list">
"""
            for item in self.report_data['diff_files']:
                diff_stats = ""
                if item['path'] in self.file_diffs:
                    diff_summary = self._get_diff_summary(self.file_diffs[item['path']])
                    diff_stats = f'<span class="diff-stats">+{diff_summary["additions"]} -{diff_summary["deletions"]}</span>'
                
                html_content += f"""
            <button class="collapsible">📄 {item['path']} - Click to view diff {diff_stats}</button>
            <div class="content">
                <div class="diff-content">
"""
                if item['path'] in self.file_diffs:
                    for line in self.file_diffs[item['path']]:
                        line_escaped = line.replace('<', '&lt;').replace('>', '&gt;')
                        if line.startswith('+++') or line.startswith('---'):
                            html_content += f'<div class="diff-info">{line_escaped}</div>\n'
                        elif line.startswith('@@'):
                            html_content += f'<div class="diff-hunk">{line_escaped}</div>\n'
                        elif line.startswith('+'):
                            html_content += f'<div class="diff-add">{line_escaped}</div>\n'
                        elif line.startswith('-'):
                            html_content += f'<div class="diff-remove">{line_escaped}</div>\n'
                        else:
                            html_content += f'<div>{line_escaped}</div>\n'
                
                html_content += """
                </div>
            </div>
"""
            html_content += "        </div>\n"
        
        html_content += """
    </div>
    <script>
        var coll = document.getElementsByClassName("collapsible");
        for (var i = 0; i < coll.length; i++) {
            coll[i].addEventListener("click", function() {
                this.classList.toggle("active");
                var content = this.nextElementSibling;
                content.classList.toggle("active");
            });
        }
    </script>
</body>
</html>
"""
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"HTML report saved to: {filename}")

def main():
    parser = argparse.ArgumentParser(description='Compare two directories and generate diff reports')
    parser.add_argument('path1', help='First directory path')
    parser.add_argument('path2', help='Second directory path')
    parser.add_argument('--format', choices=['terminal', 'table', 'tabular', 'csv', 'html', 'all'], 
                       default='terminal', help='Output format (default: terminal)')
    parser.add_argument('--output', '-o', help='Output filename (without extension)')
    
    args = parser.parse_args()
    
    if not os.path.isdir(args.path1) or not os.path.isdir(args.path2):
        print("Both arguments must be directories.")
        sys.exit(1)
    
    # Create reporter
    reporter = DiffReporter(args.path1, args.path2)
    reporter.analyze_directories()
    
    # Generate timestamp for output files
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    base_name = args.output or f"diff_report_{timestamp}"
    
    # Generate reports based on format
    if args.format in ['terminal', 'all']:
        reporter.print_colored_report()
    
    if args.format in ['table', 'all']:
        reporter.print_table_report()
    
    if args.format in ['tabular', 'all']:
        tabular_filename = f"{base_name}.txt"
        reporter.save_tabular_diff_report(tabular_filename)
    
    if args.format in ['csv', 'all']:
        csv_filename = f"{base_name}.csv"
        reporter.save_csv_report(csv_filename)
    
    if args.format in ['html', 'all']:
        html_filename = f"{base_name}.html"
        reporter.save_html_report(html_filename)

if __name__ == "__main__":
    main()
