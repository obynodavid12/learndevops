#!/bin/bash

# Set your AWS region
export AWS_DEFAULT_REGION="us-east-2"

# Define your tag key and value
tag_key="Name"
tag_value="devops_cloud"

# Filter EBS volumes by tag and state
volume_ids=$(aws ec2 describe-volumes --filters Name=tag:${tag_key},Values=${tag_value} Name=status,Values=available --query "Volumes[*].VolumeId" --output text)

# Print the volume IDs
echo "EBS volumes with tag ${tag_key}:${tag_value} in available state:"
echo "$volume_ids"

# Delete the volumes
for volume_id in $volume_ids; do
    echo "Deleting volume $volume_id"
    aws ec2 delete-volume --volume-id $volume_id
done
