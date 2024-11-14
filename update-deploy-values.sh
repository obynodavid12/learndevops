#!/bin/bash

# Define values for updates
name_key="stage-x"
channel_numbers=("100" "200" "300" "214" "400")
headend_id="101"

# Base directory where folders are located
base_directory="stage"

# Loop through each channel number to find and update the corresponding deploy.yaml
for channel_number in "${channel_numbers[@]}"; do
    # Construct the folder path for each deploy.yaml
    folder_path="$base_directory/${channel_number}_${headend_id}"
    file_path="$folder_path/deploy.yml"

    # Check if the deploy.yml file exists in the folder
    if [[ -f "$file_path" ]]; then
        # Use sed to update the placeholders with actual values
        sed -i "s/<"channel_number">/${channel_number}/g" "$file_path"
        sed -i "s/<"headend_id">/${headend_id}/g" "$file_path"
        sed -i "s/<"name_key">/${name_key}/g" "$file_path"
        
        echo "Updated $file_path with name_key=$name_key, channel_number=$channel_number, headend_id=$headend_id"
    else
        echo "File $file_path not found, skipping."
    fi
done

echo "All deploy.yml files updated successfully."
