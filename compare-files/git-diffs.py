import os
import sys
import filecmp
import difflib
from datetime import datetime
import csv
import hashlib
from typing import List, Dict, Optional, Tuple, Union
from pathlib import Path

# Color codes for terminal output
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

class FileComparison:
    """Enhanced file comparison with detailed metadata"""
    
    def __init__(self, file1: str, file2: str):
        self.file1 = file1
        self.file2 = file2
        self.added_lines = []
        self.removed_lines = []
        self.changed_lines = []
        self.unified_diff = []
        self.stats = {
            'total_lines_left': 0,
            'total_lines_right': 0,
            'additions': 0,
            'deletions': 0,
            'modifications': 0
        }
    
    def compare(self) -> bool:
        """Perform detailed file comparison"""
        try:
            # Read files with multiple encoding attempts
            left_content = self._read_file_safely(self.file1)
            right_content = self._read_file_safely(self.file2)
            
            if left_content is None or right_content is None:
                return False
            
            left_lines = left_content.splitlines(keepends=True)
            right_lines = right_content.splitlines(keepends=True)
            
            self.stats['total_lines_left'] = len(left_lines)
            self.stats['total_lines_right'] = len(right_lines)
            
            # Generate unified diff
            self.unified_diff = list(difflib.unified_diff(
                left_lines, right_lines,
                fromfile=os.path.basename(self.file1),
                tofile=os.path.basename(self.file2),
                lineterm=''
            ))
            
            # Analyze differences using SequenceMatcher for better accuracy
            matcher = difflib.SequenceMatcher(None, left_lines, right_lines)
            
            for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                if tag == 'delete':
                    self.removed_lines.extend([line.rstrip() for line in left_lines[i1:i2]])
                    self.stats['deletions'] += (i2 - i1)
                elif tag == 'insert':
                    self.added_lines.extend([line.rstrip() for line in right_lines[j1:j2]])
                    self.stats['additions'] += (j2 - j1)
                elif tag == 'replace':
                    # Mark as modifications
                    self.removed_lines.extend([line.rstrip() for line in left_lines[i1:i2]])
                    self.added_lines.extend([line.rstrip() for line in right_lines[j1:j2]])
                    self.stats['modifications'] += max(i2 - i1, j2 - j1)
            
            return True
            
        except Exception as e:
            print(f"{Colors.RED}Error comparing files {self.file1} and {self.file2}: {str(e)}{Colors.END}")
            return False
    
    def _read_file_safely(self, filepath: str) -> Optional[str]:
        """Safely read file with multiple encoding attempts"""
        encodings = ['utf-8', 'utf-16', 'latin-1', 'cp1252', 'ascii']
        
        for encoding in encodings:
            try:
                with open(filepath, 'r', encoding=encoding, errors='replace') as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
            except Exception:
                break
        
        # If all else fails, try reading as binary and convert
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
                # Try to decode as UTF-8 with error replacement
                return content.decode('utf-8', errors='replace')
        except Exception:
            return None
    
    def get_file_hash(self, filepath: str) -> str:
        """Get MD5 hash of file for integrity checking"""
        try:
            hash_md5 = hashlib.md5()
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return ""

def get_file_metadata(filepath: str) -> Dict[str, Union[str, int, float]]:
    """Get comprehensive file metadata"""
    try:
        stat = os.stat(filepath)
        return {
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
            'permissions': oct(stat.st_mode)[-3:],
            'is_binary': _is_binary_file(filepath)
        }
    except Exception:
        return {
            'size': 0,
            'modified': '',
            'created': '',
            'permissions': '',
            'is_binary': True
        }

def _is_binary_file(filepath: str) -> bool:
    """Check if file is binary"""
    try:
        with open(filepath, 'rb') as f:
            chunk = f.read(1024)
            if b'\0' in chunk:
                return True
            # Check for high ratio of non-printable characters
            text_chars = bytearray({7,8,9,10,12,13,27} | set(range(0x20, 0x100)) - {0x7f})
            return bool(chunk.translate(None, text_chars))
    except Exception:
        return True

def sanitize_for_csv(content: str, max_length: int = 32767) -> str:
    """Sanitize content for CSV output with length limit"""
    if content is None:
        return ""
    
    # Convert to string and limit length (Excel has 32767 char limit per cell)
    content = str(content)
    if len(content) > max_length:
        content = content[:max_length-3] + "..."
    
    # Replace problematic characters
    content = content.replace('\r\n', '\\n').replace('\r', '\\n').replace('\n', '\\n')
    content = content.replace('\t', '\\t').replace('\0', '\\0')
    
    return content

def generate_enhanced_csv_report(dcmp: filecmp.dircmp, output_file: str = "diff_report.csv") -> None:
    """Generate enhanced CSV diff report with comprehensive data"""
    
    def gather_comprehensive_diff_data(dcmp: filecmp.dircmp, data: List[Dict], parent_path: str = "") -> None:
        current_path = os.path.join(parent_path, os.path.basename(dcmp.left)) if parent_path else ""
        
        # Files only in left
        for name in dcmp.left_only:
            file_path = os.path.join(dcmp.left, name)
            metadata = get_file_metadata(file_path)
            
            # Try to read content for text files
            content = ""
            if not metadata['is_binary']:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read(10000)  # Limit to first 10k chars for CSV
                except Exception:
                    content = "[Unreadable text file]"
            else:
                content = f"[Binary file - {metadata['size']} bytes]"
            
            data.append({
                "type": "file",
                "status": "only_in_left",
                "path": current_path,
                "name": name,
                "difference_type": "file_only_in_left",
                "difference_summary": f"File exists only in left directory",
                "left_file_size": metadata['size'],
                "right_file_size": "",
                "left_modified": metadata['modified'],
                "right_modified": "",
                "left_hash": FileComparison("","").get_file_hash(file_path),
                "right_hash": "",
                "is_binary": metadata['is_binary'],
                "left_content_preview": sanitize_for_csv(content, 1000),
                "right_content_preview": "",
                "unified_diff": "",
                "added_lines_count": 0,
                "removed_lines_count": 0,
                "modified_lines_count": 0,
                "added_lines_sample": "",
                "removed_lines_sample": "",
                "changed_lines_sample": "",
                "full_added_lines": "",
                "full_removed_lines": "",
                "full_changed_lines": ""
            })
        
        # Files only in right
        for name in dcmp.right_only:
            file_path = os.path.join(dcmp.right, name)
            metadata = get_file_metadata(file_path)
            
            # Try to read content for text files
            content = ""
            if not metadata['is_binary']:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read(10000)  # Limit to first 10k chars for CSV
                except Exception:
                    content = "[Unreadable text file]"
            else:
                content = f"[Binary file - {metadata['size']} bytes]"
            
            data.append({
                "type": "file",
                "status": "only_in_right",
                "path": current_path,
                "name": name,
                "difference_type": "file_only_in_right",
                "difference_summary": f"File exists only in right directory",
                "left_file_size": "",
                "right_file_size": metadata['size'],
                "left_modified": "",
                "right_modified": metadata['modified'],
                "left_hash": "",
                "right_hash": FileComparison("","").get_file_hash(file_path),
                "is_binary": metadata['is_binary'],
                "left_content_preview": "",
                "right_content_preview": sanitize_for_csv(content, 1000),
                "unified_diff": "",
                "added_lines_count": 0,
                "removed_lines_count": 0,
                "modified_lines_count": 0,
                "added_lines_sample": "",
                "removed_lines_sample": "",
                "changed_lines_sample": "",
                "full_added_lines": "",
                "full_removed_lines": "",
                "full_changed_lines": ""
            })
        
        # Different files - Enhanced analysis
        for name in dcmp.diff_files:
            file1 = os.path.join(dcmp.left, name)
            file2 = os.path.join(dcmp.right, name)
            
            left_metadata = get_file_metadata(file1)
            right_metadata = get_file_metadata(file2)
            
            # Initialize comparison object
            comparison = FileComparison(file1, file2)
            comparison_success = comparison.compare()
            
            # Generate difference summary
            if comparison_success:
                diff_summary = (f"Content differs: +{comparison.stats['additions']} "
                              f"-{comparison.stats['deletions']} "
                              f"~{comparison.stats['modifications']} lines")
            else:
                diff_summary = "Files differ (binary or unreadable)"
            
            # Get content previews for text files
            left_preview = ""
            right_preview = ""
            
            if not left_metadata['is_binary']:
                try:
                    with open(file1, 'r', encoding='utf-8', errors='replace') as f:
                        left_preview = f.read(1000)
                except Exception:
                    left_preview = "[Unreadable text file]"
            else:
                left_preview = f"[Binary file - {left_metadata['size']} bytes]"
            
            if not right_metadata['is_binary']:
                try:
                    with open(file2, 'r', encoding='utf-8', errors='replace') as f:
                        right_preview = f.read(1000)
                except Exception:
                    right_preview = "[Unreadable text file]"
            else:
                right_preview = f"[Binary file - {right_metadata['size']} bytes]"
            
            # Prepare diff data
            unified_diff_text = ""
            added_sample = ""
            removed_sample = ""
            
            if comparison_success:
                unified_diff_text = sanitize_for_csv('\n'.join(comparison.unified_diff), 5000)
                
                # Create samples (first few lines)
                added_sample = sanitize_for_csv('\n'.join(comparison.added_lines[:10]), 1000)
                removed_sample = sanitize_for_csv('\n'.join(comparison.removed_lines[:10]), 1000)
                
                # Full content (with length limits)
                full_added = sanitize_for_csv('\n'.join(comparison.added_lines))
                full_removed = sanitize_for_csv('\n'.join(comparison.removed_lines))
            else:
                full_added = ""
                full_removed = ""
            
            data.append({
                "type": "file",
                "status": "different",
                "path": current_path,
                "name": name,
                "difference_type": "content_diff",
                "difference_summary": diff_summary,
                "left_file_size": left_metadata['size'],
                "right_file_size": right_metadata['size'],
                "left_modified": left_metadata['modified'],
                "right_modified": right_metadata['modified'],
                "left_hash": comparison.get_file_hash(file1),
                "right_hash": comparison.get_file_hash(file2),
                "is_binary": left_metadata['is_binary'] or right_metadata['is_binary'],
                "left_content_preview": sanitize_for_csv(left_preview),
                "right_content_preview": sanitize_for_csv(right_preview),
                "unified_diff": unified_diff_text,
                "added_lines_count": comparison.stats['additions'] if comparison_success else 0,
                "removed_lines_count": comparison.stats['deletions'] if comparison_success else 0,
                "modified_lines_count": comparison.stats['modifications'] if comparison_success else 0,
                "added_lines_sample": added_sample,
                "removed_lines_sample": removed_sample,
                "changed_lines_sample": "",  # Could be enhanced further
                "full_added_lines": full_added,
                "full_removed_lines": full_removed,
                "full_changed_lines": ""
            })
        
        # Common files with different types
        for name in dcmp.common_funny:
            data.append({
                "type": "item",
                "status": "type_different",
                "path": current_path,
                "name": name,
                "difference_type": "type_diff",
                "difference_summary": "Item type differs (e.g., file vs directory)",
                "left_file_size": "",
                "right_file_size": "",
                "left_modified": "",
                "right_modified": "",
                "left_hash": "",
                "right_hash": "",
                "is_binary": False,
                "left_content_preview": "",
                "right_content_preview": "",
                "unified_diff": "",
                "added_lines_count": 0,
                "removed_lines_count": 0,
                "modified_lines_count": 0,
                "added_lines_sample": "",
                "removed_lines_sample": "",
                "changed_lines_sample": "",
                "full_added_lines": "",
                "full_removed_lines": "",
                "full_changed_lines": ""
            })
        
        # Recurse into subdirectories
        for sub_name, sub_dcmp in dcmp.subdirs.items():
            data.append({
                "type": "directory",
                "status": "compared",
                "path": current_path,
                "name": sub_name,
                "difference_type": "subdirectory",
                "difference_summary": "Subdirectory comparison",
                "left_file_size": "",
                "right_file_size": "",
                "left_modified": "",
                "right_modified": "",
                "left_hash": "",
                "right_hash": "",
                "is_binary": False,
                "left_content_preview": "",
                "right_content_preview": "",
                "unified_diff": "",
                "added_lines_count": 0,
                "removed_lines_count": 0,
                "modified_lines_count": 0,
                "added_lines_sample": "",
                "removed_lines_sample": "",
                "changed_lines_sample": "",
                "full_added_lines": "",
                "full_removed_lines": "",
                "full_changed_lines": ""
            })
            
            next_path = os.path.join(current_path, sub_name) if current_path else sub_name
            gather_comprehensive_diff_data(sub_dcmp, data, next_path)
    
    # Gather all difference data
    csv_data = []
    gather_comprehensive_diff_data(dcmp, csv_data)
    
    # Define comprehensive fieldnames
    fieldnames = [
        'type', 'status', 'path', 'name', 'difference_type', 'difference_summary',
        'left_file_size', 'right_file_size', 'left_modified', 'right_modified',
        'left_hash', 'right_hash', 'is_binary',
        'left_content_preview', 'right_content_preview', 'unified_diff',
        'added_lines_count', 'removed_lines_count', 'modified_lines_count',
        'added_lines_sample', 'removed_lines_sample', 'changed_lines_sample',
        'full_added_lines', 'full_removed_lines', 'full_changed_lines'
    ]
    
    # Write to CSV with proper handling
    try:
        with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:  # BOM for Excel
            writer = csv.DictWriter(
                csvfile,
                fieldnames=fieldnames,
                quoting=csv.QUOTE_ALL,
                escapechar='\\',
                quotechar='"',
                delimiter=','
            )
            
            writer.writeheader()
            writer.writerows(csv_data)
        
        print(f"\n{Colors.GREEN}Enhanced CSV report generated: {output_file}{Colors.END}")
        print(f"{Colors.CYAN}Records written: {len(csv_data)}{Colors.END}")
        
        # Generate summary statistics
        stats = {
            'only_left': len([r for r in csv_data if r['status'] == 'only_in_left']),
            'only_right': len([r for r in csv_data if r['status'] == 'only_in_right']),
            'different': len([r for r in csv_data if r['status'] == 'different']),
            'directories': len([r for r in csv_data if r['type'] == 'directory'])
        }
        
        print(f"{Colors.YELLOW}Summary: {stats['only_left']} left-only, {stats['only_right']} right-only, "
              f"{stats['different']} different, {stats['directories']} directories{Colors.END}")
        
    except Exception as e:
        print(f"{Colors.RED}Error writing CSV file: {str(e)}{Colors.END}")

def generate_html_diff_report(dcmp: filecmp.dircmp, output_file: str = "diff_report.html") -> None:
    """Generate a beautiful HTML diff report with enhanced styling"""
    
    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Folder Diff Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</title>
    <style>
        :root {{
            --primary-color: #3498db;
            --secondary-color: #2ecc71;
            --danger-color: #e74c3c;
            --warning-color: #f39c12;
            --light-color: #ecf0f1;
            --dark-color: #34495e;
            --text-color: #2c3e50;
            --border-color: #bdc3c7;
        }}
        
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: var(--text-color);
            background-color: #f9f9f9;
            padding: 0;
            margin: 0;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        header {{
            background-color: var(--dark-color);
            color: white;
            padding: 20px 0;
            margin-bottom: 30px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        
        .header-content {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
        }}
        
        h1 {{
            font-size: 2.2rem;
            margin-bottom: 10px;
        }}
        
        .report-meta {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        
        .summary-card {{
            background-color: white;
            border-radius: 8px;
            padding: 25px;
            margin-bottom: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }}
        
        .path-display {{
            display: flex;
            gap: 20px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }}
        
        .path-box {{
            flex: 1;
            min-width: 300px;
            background-color: var(--light-color);
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid var(--primary-color);
        }}
        
        .path-box.right {{
            border-left-color: var(--secondary-color);
        }}
        
        .path-label {{
            font-weight: bold;
            margin-bottom: 5px;
            color: var(--dark-color);
        }}
        
        .diff-section {{
            margin-bottom: 40px;
        }}
        
        .section-title {{
            font-size: 1.4rem;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid var(--border-color);
            color: var(--dark-color);
        }}
        
        .diff-item {{
            background-color: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            overflow: hidden;
        }}
        
        .diff-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }}
        
        .diff-title {{
            font-size: 1.2rem;
            font-weight: bold;
            color: var(--dark-color);
        }}
        
        .diff-status {{
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 0.9rem;
            font-weight: bold;
        }}
        
        .status-only-left {{
            background-color: #fde8e8;
            color: var(--danger-color);
        }}
        
        .status-only-right {{
            background-color: #e8f8f0;
            color: var(--secondary-color);
        }}
        
        .status-different {{
            background-color: #fff4e0;
            color: var(--warning-color);
        }}
        
        .diff-content {{
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            white-space: pre-wrap;
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            overflow-x: auto;
        }}
        
        .diff-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}
        
        .diff-table th {{
            background-color: var(--light-color);
            padding: 10px;
            text-align: left;
        }}
        
        .diff-table td {{
            padding: 8px 10px;
            border-bottom: 1px solid var(--border-color);
        }}
        
        .diff-added {{
            background-color: #e8f8f0;
        }}
        
        .diff-added-line {{
            background-color: #d4eddf;
            font-weight: bold;
        }}
        
        .diff-removed {{
            background-color: #fde8e8;
        }}
        
        .diff-removed-line {{
            background-color: #f5d5d5;
            font-weight: bold;
        }}
        
        .diff-changed {{
            background-color: #fff4e0;
        }}
        
        .diff-line-number {{
            color: #7f8c8d;
            padding-right: 15px;
            border-right: 1px solid var(--border-color);
        }}
        
        .subdirectory {{
            margin-left: 20px;
            border-left: 2px solid var(--border-color);
            padding-left: 20px;
        }}
        
        .timestamp {{
            color: #7f8c8d;
            font-size: 0.9rem;
        }}
        
        @media (max-width: 768px) {{
            .path-display {{
                flex-direction: column;
                gap: 10px;
            }}
            
            .path-box {{
                min-width: 100%;
            }}
        }}
    </style>
</head>
<body>
    <header>
        <div class="header-content">
            <h1>Folder Comparison Report</h1>
            <div class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>
    </header>
    
    <div class="container">
        <div class="summary-card">
            <div class="path-display">
                <div class="path-box">
                    <div class="path-label">Left Path:</div>
                    <div class="path-value">{dcmp.left}</div>
                </div>
                <div class="path-box right">
                    <div class="path-label">Right Path:</div>
                    <div class="path-value">{dcmp.right}</div>
                </div>
            </div>
        </div>
        <!-- CONTENT WILL BE INSERTED HERE -->
    </div>
</body>
</html>
"""
    
    def build_html_content(dcmp: filecmp.dircmp, content: List[str], level: int = 0) -> None:
        indent = "    " * level
        subdir_class = " subdirectory" if level > 0 else ""
        
        # Files only in left
        if dcmp.left_only:
            content.append(f'{indent}<div class="diff-section{subdir_class}">')
            content.append(f'{indent}    <h2 class="section-title">Only in {os.path.basename(dcmp.left)}</h2>')
            for name in sorted(dcmp.left_only):
                content.append(f'{indent}    <div class="diff-item">')
                content.append(f'{indent}        <div class="diff-header">')
                content.append(f'{indent}            <div class="diff-title">{name}</div>')
                content.append(f'{indent}            <div class="diff-status status-only-left">Only in left</div>')
                content.append(f'{indent}        </div>')
                content.append(f'{indent}    </div>')
            content.append(f'{indent}</div>')
        
        # Files only in right
        if dcmp.right_only:
            content.append(f'{indent}<div class="diff-section{subdir_class}">')
            content.append(f'{indent}    <h2 class="section-title">Only in {os.path.basename(dcmp.right)}</h2>')
            for name in sorted(dcmp.right_only):
                content.append(f'{indent}    <div class="diff-item">')
                content.append(f'{indent}        <div class="diff-header">')
                content.append(f'{indent}            <div class="diff-title">{name}</div>')
                content.append(f'{indent}            <div class="diff-status status-only-right">Only in right</div>')
                content.append(f'{indent}        </div>')
                content.append(f'{indent}    </div>')
            content.append(f'{indent}</div>')
        
        # Different files
        if dcmp.diff_files:
            content.append(f'{indent}<div class="diff-section{subdir_class}">')
            content.append(f'{indent}    <h2 class="section-title">Different Files</h2>')
            for name in sorted(dcmp.diff_files):
                file1 = os.path.join(dcmp.left, name)
                file2 = os.path.join(dcmp.right, name)
                
                content.append(f'{indent}    <div class="diff-item">')
                content.append(f'{indent}        <div class="diff-header">')
                content.append(f'{indent}            <div class="diff-title">{name}</div>')
                content.append(f'{indent}            <div class="diff-status status-different">Different</div>')
                content.append(f'{indent}        </div>')
                
                try:
                    with open(file1, 'r', encoding='utf-8', errors='ignore') as f1, \
                         open(file2, 'r', encoding='utf-8', errors='ignore') as f2:
                        f1_lines = f1.readlines()
                        f2_lines = f2.readlines()
                        
                        # Generate unified diff
                        diff = difflib.unified_diff(
                            f1_lines, f2_lines,
                            fromfile=os.path.basename(file1),
                            tofile=os.path.basename(file2),
                            lineterm=''
                        )
                        
                        # Generate HTML for the diff
                        diff_html = []
                        for line in diff:
                            if line.startswith('---'):
                                continue
                            elif line.startswith('+++'):
                                continue
                            elif line.startswith('@@'):
                                diff_html.append(f'<div class="diff-changed"><strong>{line}</strong></div>')
                            elif line.startswith('+'):
                                diff_html.append(f'<div class="diff-added-line">{line}</div>')
                            elif line.startswith('-'):
                                diff_html.append(f'<div class="diff-removed-line">{line}</div>')
                            else:
                                diff_html.append(f'<div>{line}</div>')
                        
                        content.append(f'{indent}        <div class="diff-content">')
                        content.extend([f'{indent}            {line}' for line in diff_html])
                        content.append(f'{indent}        </div>')
                        
                        # Add detailed line-by-line comparison table
                        comparison = FileComparison(file1, file2)
                        if comparison.compare():
                            added, removed, changed = comparison.added_lines, comparison.removed_lines, comparison.changed_lines
                            
                            if added or removed or changed:
                                content.append(f'{indent}        <div style="margin-top: 20px;">')
                                content.append(f'{indent}            <h3 style="font-size: 1.1rem; margin-bottom: 10px;">Detailed Changes:</h3>')
                                
                                if added:
                                    content.append(f'{indent}            <div style="margin-bottom: 15px;">')
                                    content.append(f'{indent}                <h4 style="color: var(--secondary-color); margin-bottom: 5px;">Added Lines ({len(added)}):</h4>')
                                    content.append(f'{indent}                <div class="diff-content diff-added">')
                                    content.extend([f'{indent}                    <div>+ {line}</div>' for line in added[:10]])
                                    if len(added) > 10:
                                        content.append(f'{indent}                    <div>... {len(added)-10} more lines ...</div>')
                                    content.append(f'{indent}                </div>')
                                    content.append(f'{indent}            </div>')
                                
                                if removed:
                                    content.append(f'{indent}            <div style="margin-bottom: 15px;">')
                                    content.append(f'{indent}                <h4 style="color: var(--danger-color); margin-bottom: 5px;">Removed Lines ({len(removed)}):</h4>')
                                    content.append(f'{indent}                <div class="diff-content diff-removed">')
                                    content.extend([f'{indent}                    <div>- {line}</div>' for line in removed[:10]])
                                    if len(removed) > 10:
                                        content.append(f'{indent}                    <div>... {len(removed)-10} more lines ...</div>')
                                    content.append(f'{indent}                </div>')
                                    content.append(f'{indent}            </div>')
                                
                                if changed:
                                    content.append(f'{indent}            <div>')
                                    content.append(f'{indent}                <h4 style="color: var(--warning-color); margin-bottom: 5px;">Changed Lines ({len(changed)}):</h4>')
                                    content.append(f'{indent}                <div class="diff-content diff-changed">')
                                    content.extend([f'{indent}                    <div>? {line}</div>' for line in changed[:10]])
                                    if len(changed) > 10:
                                        content.append(f'{indent}                    <div>... {len(changed)-10} more lines ...</div>')
                                    content.append(f'{indent}                </div>')
                                    content.append(f'{indent}            </div>')
                                
                                content.append(f'{indent}        </div>')
                
                except Exception as e:
                    content.append(f'{indent}        <div class="diff-content" style="color: var(--danger-color);">')
                    content.append(f'{indent}            Error processing {name}: {str(e)}')
                    content.append(f'{indent}        </div>')
                
                content.append(f'{indent}    </div>')
            content.append(f'{indent}</div>')
        
        # Recurse into subdirectories
        for sub_name, sub_dcmp in sorted(dcmp.subdirs.items()):
            build_html_content(sub_dcmp, content, level + 1)
    
    html_content = []
    build_html_content(dcmp, html_content)
    
    # Insert content into template and save
    full_html = html_template.replace("<!-- CONTENT WILL BE INSERTED HERE -->", "\n".join(html_content))
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(full_html)
    
    print(f"\n{Colors.GREEN}HTML report generated: {output_file}{Colors.END}")

def print_color_diff(dcmp: filecmp.dircmp) -> None:
    """Print colorized diff to terminal"""
    
    def print_diff(dcmp: filecmp.dircmp, level: int = 0) -> None:
        indent = "  " * level
        
        # Print directory comparison header
        if level == 0:
            print(f"\n{Colors.BOLD}Comparing:{Colors.END}")
            print(f"{Colors.CYAN}  Left:  {dcmp.left}{Colors.END}")
            print(f"{Colors.CYAN}  Right: {dcmp.right}{Colors.END}\n")
        else:
            print(f"\n{indent}{Colors.BOLD}Subdirectory: {os.path.basename(dcmp.left)}{Colors.END}")
        
        # Files only in left
        if dcmp.left_only:
            print(f"{indent}{Colors.YELLOW}Only in {os.path.basename(dcmp.left)}:{Colors.END}")
            for name in sorted(dcmp.left_only):
                print(f"{indent}  {Colors.RED}- {name}{Colors.END}")
        
        # Files only in right
        if dcmp.right_only:
            print(f"{indent}{Colors.YELLOW}Only in {os.path.basename(dcmp.right)}:{Colors.END}")
            for name in sorted(dcmp.right_only):
                print(f"{indent}  {Colors.GREEN}+ {name}{Colors.END}")
        
        # Different files
        if dcmp.diff_files:
            print(f"{indent}{Colors.YELLOW}Different files:{Colors.END}")
            for name in sorted(dcmp.diff_files):
                file1 = os.path.join(dcmp.left, name)
                file2 = os.path.join(dcmp.right, name)
                
                print(f"\n{indent}{Colors.MAGENTA}File: {name}{Colors.END}")
                
                try:
                    comparison = FileComparison(file1, file2)
                    if comparison.compare():
                        print(f"{indent}  Summary: {Colors.GREEN}{len(comparison.added_lines)} added{Colors.END}, "
                              f"{Colors.RED}{len(comparison.removed_lines)} removed{Colors.END}, "
                              f"{Colors.YELLOW}{len(comparison.changed_lines)} changed{Colors.END} lines")
                        
                        # Print unified diff
                        for line in comparison.unified_diff:
                            if line.startswith('---'):
                                print(f"{indent}{Colors.CYAN}{line}{Colors.END}")
                            elif line.startswith('+++'):
                                print(f"{indent}{Colors.CYAN}{line}{Colors.END}")
                            elif line.startswith('+'):
                                print(f"{indent}{Colors.GREEN}{line}{Colors.END}")
                            elif line.startswith('-'):
                                print(f"{indent}{Colors.RED}{line}{Colors.END}")
                            elif line.startswith('@'):
                                print(f"{indent}{Colors.BLUE}{line}{Colors.END}")
                            else:
                                print(f"{indent}{line}")
                except Exception as e:
                    print(f"{indent}{Colors.RED}Error comparing {name}: {str(e)}{Colors.END}")
        
        # Recurse into subdirectories
        for sub_name, sub_dcmp in sorted(dcmp.subdirs.items()):
            print_diff(sub_dcmp, level + 1)
    
    print_diff(dcmp)

def main():
    if len(sys.argv) not in [3, 4]:
        print(f"{Colors.RED}USAGE: python folder_diff.py path1 path2 [output_format]{Colors.END}")
        print("Available formats: console (default), html, csv, enhanced-csv, all")
        sys.exit(2)

    path1 = sys.argv[1]
    path2 = sys.argv[2]
    output_format = sys.argv[3] if len(sys.argv) == 4 else "console"

    if not os.path.isdir(path1) or not os.path.isdir(path2):
        print(f"{Colors.RED}Both arguments must be directories.{Colors.END}")
        sys.exit(1)

    print(f"{Colors.CYAN}Starting comparison...{Colors.END}")
    dcmp = filecmp.dircmp(path1, path2)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if output_format.lower() == "console" or output_format.lower() == "all":
        print_color_diff(dcmp)
    
    if output_format.lower() == "html" or output_format.lower() == "all":
        html_file = f"diff_report_{timestamp}.html"
        generate_html_diff_report(dcmp, html_file)
    
    if output_format.lower() in ["csv", "enhanced-csv"] or output_format.lower() == "all":
        csv_file = f"enhanced_diff_report_{timestamp}.csv"
        generate_enhanced_csv_report(dcmp, csv_file)

if __name__ == "__main__":
    main()

def generate_tabular_diff_report(dcmp: filecmp.dircmp, output_file: str = "output.txt") -> None:
    """Generate a clean tabular diff report without ANSI colors or truncation"""
    
    COLUMN_WIDTH = 80  # Wider columns to show more content
    SEPARATOR = " | "
    LINE_LENGTH = COLUMN_WIDTH * 2 + len(SEPARATOR)
    
    def format_line(line: str) -> str:
        """Format a line for display without truncation"""
        line = line.rstrip('\n').replace('\t', '    ')
        return line.ljust(COLUMN_WIDTH)[:COLUMN_WIDTH]  # Pad but don't truncate
    
    def write_file_comparison(file1: str, file2: str, f) -> None:
        """Write a full comparison of two files without truncation"""
        try:
            with open(file1, 'r', encoding='utf-8', errors='replace') as f1, \
                 open(file2, 'r', encoding='utf-8', errors='replace') as f2:
                left_lines = f1.readlines()
                right_lines = f2.readlines()
                
                # Write header
                f.write(f"\nComparing: {os.path.basename(file1)} vs {os.path.basename(file2)}\n")
                f.write("-" * LINE_LENGTH + "\n")
                f.write("LEFT".center(COLUMN_WIDTH) + SEPARATOR + "RIGHT".center(COLUMN_WIDTH) + "\n")
                f.write("-" * LINE_LENGTH + "\n")
                
                # Use unified diff to show changes
                differ = difflib.Differ()
                diff = list(differ.compare(left_lines, right_lines))
                
                left_pos = 0
                right_pos = 0
                
                for line in diff:
                    if line.startswith('  '):  # Unchanged
                        left = format_line(left_lines[left_pos])
                        right = format_line(right_lines[right_pos])
                        f.write(left + SEPARATOR + right + "\n")
                        left_pos += 1
                        right_pos += 1
                    elif line.startswith('- '):  # Removed
                        left = format_line(left_lines[left_pos])
                        f.write(left + SEPARATOR + " " * COLUMN_WIDTH + "\n")
                        left_pos += 1
                    elif line.startswith('+ '):  # Added
                        right = format_line(right_lines[right_pos])
                        f.write(" " * COLUMN_WIDTH + SEPARATOR + right + "\n")
                        right_pos += 1
                    elif line.startswith('? '):  # Changed
                        # Show both versions with markers
                        left = format_line(left_lines[left_pos-1])
                        right = format_line(right_lines[right_pos-1])
                        f.write(left + SEPARATOR + right + "\n")
                        f.write("^" * COLUMN_WIDTH + SEPARATOR + "^" * COLUMN_WIDTH + "\n")
                
                # Add summary
                f.write("-" * LINE_LENGTH + "\n")
                stats = {
                    'left_lines': len(left_lines),
                    'right_lines': len(right_lines),
                    'added': sum(1 for line in diff if line.startswith('+ ')),
                    'removed': sum(1 for line in diff if line.startswith('- '))
                }
                f.write(f"Summary: Left={stats['left_lines']} lines, Right={stats['right_lines']} lines | "
                       f"Added: {stats['added']}, Removed: {stats['removed']}\n")
                
        except Exception as e:
            f.write(f"\nError comparing files: {str(e)}\n")
    
    def gather_tabular_data(dcmp: filecmp.dircmp, f, level: int = 0) -> None:
        """Recursively gather data for tabular output"""
        indent = "  " * level
        
        # Files only in left
        if dcmp.left_only:
            f.write(f"\n{indent}Files only in {os.path.basename(dcmp.left)}:\n")
            for name in sorted(dcmp.left_only):
                f.write(f"{indent}- {name}\n")
        
        # Files only in right
        if dcmp.right_only:
            f.write(f"\n{indent}Files only in {os.path.basename(dcmp.right)}:\n")
            for name in sorted(dcmp.right_only):
                f.write(f"{indent}+ {name}\n")
        
        # Different files
        if dcmp.diff_files:
            f.write(f"\n{indent}Different files:\n")
            for name in sorted(dcmp.diff_files):
                file1 = os.path.join(dcmp.left, name)
                file2 = os.path.join(dcmp.right, name)
                write_file_comparison(file1, file2, f)
        
        # Recurse into subdirectories
        for sub_name, sub_dcmp in sorted(dcmp.subdirs.items()):
            f.write(f"\n{indent}Subdirectory: {sub_name}\n")
            gather_tabular_data(sub_dcmp, f, level + 1)
    
    # Generate the report
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"Folder Comparison Report\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Left: {dcmp.left}\n")
        f.write(f"Right: {dcmp.right}\n")
        f.write("=" * LINE_LENGTH + "\n")
        
        gather_tabular_data(dcmp, f)
        
        # Add summary
        f.write("\n" + "=" * LINE_LENGTH + "\n")
        f.write("Comparison complete.\n")
    
    print(f"\n{Colors.GREEN}Tabular diff report generated: {output_file}")

# [Update main function to include tabular option]
def main():
    if len(sys.argv) not in [3, 4]:
        print(f"USAGE: python folder_diff.py path1 path2 [output_format]")
        print("Available formats: console (default), html, csv, enhanced-csv, tabular, all")
        sys.exit(2)

    path1 = sys.argv[1]
    path2 = sys.argv[2]
    output_format = sys.argv[3] if len(sys.argv) == 4 else "console"

    if not os.path.isdir(path1) or not os.path.isdir(path2):
        print(f"Both arguments must be directories.")
        sys.exit(1)

    print(f"{Colors.YELLOW}Starting comparison...{Colors.END}")
    dcmp = filecmp.dircmp(path1, path2)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if output_format.lower() == "console" or output_format.lower() == "all":
        print_color_diff(dcmp)
    
    if output_format.lower() == "html" or output_format.lower() == "all":
        html_file = f"diff_report_{timestamp}.html"
        generate_html_diff_report(dcmp, html_file)
    
    if output_format.lower() in ["csv", "enhanced-csv"] or output_format.lower() == "all":
        csv_file = f"enhanced_diff_report_{timestamp}.csv"
        generate_enhanced_csv_report(dcmp, csv_file)
    
    if output_format.lower() in ["tabular", "all"]:
        tabular_file = f"tabular_diff_{timestamp}.txt"
        generate_tabular_diff_report(dcmp, tabular_file)

if __name__ == "__main__":
    main()
