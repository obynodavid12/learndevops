sed -r 's/\x1B\[[0-9;]*[mK]//g' Compare-files/diffs.txt > Compare-files/diffs_clean.txt


# HOW TO USE git-diffs.py
How to Use:
Basic usage (color terminal output):
python folder_diff.py path1 path2

HTML report:
python folder_diff.py path1 path2 html

# To view it in html format
Execute the below command.
python3 -m http.server - Then open webbrowser and type in localhost:8000 boom - Welcome to my Website Register or Login
python3 -m http.server 2000  --(if this prints an error, try with other ports 2000 or 8888 7777 etc)
Serving HTTP on 0.0.0.0 port 8000 (http://0.0.0.0:8000/) ...


CSV report:
python folder_diff.py path1 path2 csv

All report types:
python folder_diff.py path1 path2 all



# HOW TO USE git-diff.py 
# Quick terminal comparison with colors
# Basic usage (colored terminal output)
python3 git-diff.py path1 path2

# Generate HTML report
python3 git-diff.py path1 path2 --format html --output my_report


# Table format output
python git-diff.py /path/to/dir1 /path/to/dir2 --format table

# Enhanced CSV with diff details
python git-diff.py /path/to/dir1 /path/to/dir2 --format csv --output detailed_comparison

# All formats
python git-diff.py /path/to/dir1 /path/to/dir2 --format all --output complete_report

# Generate tabular diff report
python git-diff /path/to/deploy-1 /path/to/deploy-2 --format tabular

# Generate with custom filename
python git-diff /path/to/deploy-1 /path/to/deploy-2 --format tabular --output folder_comparison

# Generate all formats including tabular
python git-diff /path/to/deploy-1 /path/to/deploy-2 --format all

# To view it in html format
Execute the below command.
python3 -m http.server - Then open webbrowser and type in localhost:8000 boom - Welcome to my Website Register or Login
python3 -m http.server 2000  --(if this prints an error, try with other ports 2000 or 8888 7777 etc)
Serving HTTP on 0.0.0.0 port 8000 (http://0.0.0.0:8000/) ...


# Generate all formats
python folder_diff.py path1 path2 --format all --output comparison_2024

OR


python folder_diff.py /path/to/dir1 /path/to/dir2

# Generate beautiful HTML report
python git-diff /path/to/dir1 /path/to/dir2 --format html -o project_comparison

# Create all formats at once
python git-diff /path/to/dir1 /path/to/dir2 --format all -o backup_analysis

# CSV for data analysis
python git-diff /path/to/dir1 /path/to/dir2 --format csv -o data_export




folder1-diffs.py commands
# Save report format to file (no colors in file)
python3 folder1-diffs.py -r -o comparison_report.txt deploy-1 deploy-2

# Save tabular summary to file
python3 folder1-diffs.py -t -o summary.txt deploy-1 deploy-2

# Save unified diff to file
python3 folder1-diffs.py -u -o changes.txt deploy-1 deploy-2

# Save report format with custom width
python3 folder1-diffs.py -r --width 200 -o wide_report.txt deploy-1 deploy-2
