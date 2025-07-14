#!/bin/bash

# More robust version for nested directories
find learndevops -type f -print0 | while IFS= read -r -d '' source_file; do
    # Get relative path
    rel_path=$(realpath --relative-to=learndevops "$source_file")
    target_file="Scripts/$rel_path"
    
    # Check if target exists
    if [[ ! -f "$target_file" ]]; then
        echo "❌ Missing in Scripts/: $rel_path"
        continue
    fi
    
    # Compare files
    if ! cmp --silent "$source_file" "$target_file"; then
        echo "=== Differences in: $rel_path ==="
        diff -u "$source_file" "$target_file"
        echo
    fi
done

# Also check for files that exist in Scripts/ but not in learndevops/
echo "=== Checking for extra files in Scripts/ ==="
find Scripts -type f -print0 | while IFS= read -r -d '' target_file; do
    rel_path=$(realpath --relative-to=Scripts "$target_file")
    source_file="learndevops/$rel_path"
    
    if [[ ! -f "$source_file" ]]; then
        echo "❌ Extra file in Scripts/: $rel_path"
    fi
done
