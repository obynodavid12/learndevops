#!/bin/bash

declare -A update_map=(
  ["X-TEST"]="https://172.10.9.10:2022 200 250"
  ["Y-TEST"]="https://172.20.9.10:2035 210 260"
  ["Z-TEST"]="172.200.9.10:2055 220 270"
  ["SAMPLE-TEST"]="https://172.110.19.10:2028 230 280"
)

json='{"files": ["x-test.json", "y-test.json", "z-test.json", "sample.json"]}'

echo "$json" | jq -r '.files[]' | while read -r file; do
  [[ ! -f "$file" ]] && { echo "Warning: $file not found"; continue; }
  
  cp "$file" "$file.bak"  # 🔒 Backup before modification
  
  # Process each update mapping
  for device_name in "${!update_map[@]}"; do
    IFS=' ' read -r url pp sp <<< "${update_map[$device_name]}"
    
    # Update stream_url
    jq --arg name "$device_name" --arg url "$url" \
       '(.phone[] | select(.name == $name) | .stream_url) = $url' \
       "$file" > tmp.json && mv tmp.json "$file"
    
    # Update purchase_price  
    jq --arg name "$device_name" --argjson price "$pp" \
       '(.phone[] | select(.name == $name) | .purchase_price) = $price' \
       "$file" > tmp.json && mv tmp.json "$file"
    
    # Update sales_price
    jq --arg name "$device_name" --argjson price "$sp" \
       '(.phone[] | select(.name == $name) | .sales_price) = $price' \
       "$file" > tmp.json && mv tmp.json "$file"
  done
  
  echo "Updated $file successfully!"
done





# # Automate JSON Updates via CI/CD (Optional)- Using tools like Jenkins, GitLab CI, or GitHub Actions, you can add this script to your pipeline to automate configuration updates before deployment. Simply add a step that runs your Bash script.
# jobs:
#   build:
#     runs-on: ubuntu-latest
#     steps:
#     - uses: actions/checkout@v2
#     - name: Update JSON Config
#       run: ./update_config.sh

