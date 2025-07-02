#!/bin/bash

# Device-specific updates
declare -A device_updates=(
  ["X-TEST"]="https://10.0.0.1:8000 100 150"
  ["Y-TEST"]="https://10.0.0.2:8000 110 160"
  ["Z-TEST"]="https://10.0.0.3:8000 120 170"
  ["SAMPLE-TEST"]="https://10.0.0.4:8000 130 180"
)

# Files to update
files=("x-test.json" "y-test.json" "z-test.json" "sample.json")

for file in "${files[@]}"; do
  echo "Backing up $file..."
  cp "$file" "$file.bak"

  for device in "${!device_updates[@]}"; do
    IFS=' ' read -r url pp sp <<< "${device_updates[$device]}"

    jq --arg name "$device" \
       --arg url "$url" \
       --argjson pp "$pp" \
       --argjson sp "$sp" '
      .phone |= map(
        if (.name | ascii_downcase) == ($name | ascii_downcase)
        then .stream_url = $url
             | .purchase_price = $pp
             | .sales_price = $sp
        else .
        end
      )
    ' "$file" > tmp.json && mv tmp.json "$file"
  done

  echo "Updated $file ✅"
done
