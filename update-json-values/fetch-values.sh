# #!/bin/bash

# json='{"files": ["x-test.json", "y-test.json", "z-test.json", "sample.json"]}'

# # Extract file list and iterate
# echo "$json" | jq -r '.files[]' | while read -r file; do
#   jq -r '.phone[]?.stream_url // empty' "$file"
# done

# #!/bin/bash

# json='{"files": ["x-test.json", "y-test.json", "z-test.json", "sample.json"]}'

# echo "$json" | jq -r '.files[]' | while read -r file; do
#     [[ -f "$file" ]] && jq -r '.phone[]?.stream_url // empty' "$file" 2>/dev/null
# done



# #!/bin/bash

# json='{"files": ["x-test.json", "y-test.json", "z-test.json", "sample.json"]}'

# for file in $(echo "$json" | jq -r '.files[]'); do
#     if [[ -f "$file" ]]; then
#         jq -r '.phone[] | select(.stream_url) | .stream_url' "$file"
#     fi
# done


# #!/bin/bash

# json='{"files": ["x-test.json", "y-test.json", "z-test.json", "sample.json"]}'

# # Process each file and extract stream_url
# echo "$json" | jq -r '.files[]' | while read -r file; do
#     if [ -f "$file" ]; then
#         # Extract stream_url from phone array where it exists
#         # jq -r '.phone[] | select(.stream_url != null) | .stream_url' "$file"
#         jq -r --arg f "$file" '.phone[] | select(.stream_url != null) | "\($f): \(.stream_url)"' "$file"
#     else
#         echo "File not found: $file" >&2
#     fi
# done

# #!/bin/bash

# # JSON containing the list of files
# json='{"files": ["x-test.json", "y-test.json", "z-test.json", "sample.json"]}'

# # Extract file names from the JSON
# files=$(echo "$json" | jq -r '.files[]')

# # Loop through each file and extract the stream_url
# for file in $files; do
#   # Assuming the JSON file structure is the same as provided
#   # Read the file and filter the stream_url
#   stream_url=$(jq -r '.phone[] | select(.stream_url != null) | .stream_url' "$file")
  
#   # Print the stream_url if it exists
#   if [[ -n "$stream_url" ]]; then
#     echo "$stream_url"
#   fi
# done


# FILTER MULTIPLE VALUES FROM JSON FILES

# #!/bin/bash

# json='{"files": ["x-test.json", "y-test.json", "z-test.json", "sample.json"]}'
# output_file="output.txt"

# > "$output_file"  # Clear output file

# echo "$json" | jq -r '.files[]' | while read -r file; do
#   jq -r --arg file "$file" '
#     .phone[]? | select(.stream_url or .purchase_price or .sales_price) |
#     "\($file): stream_url=\(.stream_url // "N/A"), purchase_price=\(.purchase_price // "N/A"), sales_price=\(.sales_price // "N/A")"
#   ' "$file" >> "$output_file"
# done
