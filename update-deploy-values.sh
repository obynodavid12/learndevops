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


# #!/bin/bash

# Input data as variables
nums='NUM-1 NUM-2 NUM-3 NUM-4 NUM-5 NUM-6 NUM-7'
ids='172.23.13.64:2010 172.23.13.65:2020 172.23.13.66:2030 172.23.13.67:2040 172.23.13.68:2050 172.23.13.69:2160 172.23.13.70:2170'
keys="ete5ebdtdbnflfbcf
gdkdhmklk56nnn0bdbd
rqdjlhnlkdq759bnan
jgjcGDtfdgaefneg848
irithgn858ffhkmb56
kjfjqjhk8774bjalkd
ugfuytfrgn9458y34"

# Read keys and nums into arrays
IFS=$' ' read -r -a num_array <<< "$nums"
IFS=$' ' read -r -a id_array <<< "$ids"
IFS=$'\n' read -r -d '' -a key_array <<< "$keys"

# Directory to store output files
output_dir="./output"

# Ensure the template file exists
template_file="/home/devops_cloud/script/file-mgt/ec2-instance.yaml"
if [[ ! -f "$template_file" ]]; then
    echo "Error: Template file not found: $template_file" >&2
    exit 1
fi

# Create output directory if it doesn't exist
mkdir -p "$output_dir"

# Check if the arrays have matching lengths
if [[ ${#num_array[@]} -ne ${#id_array[@]} || ${#id_array[@]} -ne ${#key_array[@]} ]]; then
    echo "Error: Mismatched array lengths" >&2
    exit 1
fi

# Process each entry
for i in "${!num_array[@]}"; do
    num="${num_array[i]}"
    id="${id_array[i]}"
    key="${key_array[i]}"
    output_file="$output_dir/ec2-instance-$num.yaml"

    # Debugging: Show the current entry being processed
    echo "Processing: $num, $id, $key"

    # Copy template file to new output file
    if cp "$template_file" "$output_file"; then
        echo "Template copied to $output_file"
    else
        echo "Failed to copy template to $output_file" >&2
        continue
    fi

    # Modify the file using sed
    if sed -i \
        -e "s/<filename>/$num/g" \
        -e "s/<fileid>/$id/g" \
        -e "s/<kdlparamskeys>/$key/g" \
        "$output_file"; then
        echo "Successfully modified $output_file"
    else
        echo "Failed to modify $output_file" >&2
    fi
done

echo "All files processed."
