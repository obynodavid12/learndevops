#!/bin/bash

#Terminal Colours
BLUE_TEXT='\033[0;34m'
GREEN_TEXT='\033[0;32m'
RED_TEXT='\033[0;31m'

# Variables
namespace="default"
file_to_copy="patch.yaml"        # Local file to copy (path to the file)
dest_path="/mnt/" # Destination path in the pod
service_status="nginx -V"     # Check Nginx status
# nginx_logs="cat /var/log/nginx/error.log" # View Nginx logs
# nginx_restart="nginx -s reload" # Restart Nginx

# Check if the file exists
if [ ! -f "$file_to_copy" ]; then
  echo -e "${RED_TEXT}Error: File $file_to_copy does not exist."
  exit 1
fi

# Get the list of pods in the namespace
pods=$(kubectl get pods -n $namespace --no-headers=true | awk '{print $1}' | grep 'nginx-deployment')

# Loop through each pod
 for pod in $pods; do
   if [[ $pod == *"nginx-deployment"* ]]; then
   echo -e "${BLUE_TEXT}Matching nginx-deployment pod found: $pod${GREEN_TEXT}"
   #echo -e "${BLUE_TEXT}Processing pods: $pods${GREEN_TEXT}"
   fi

# Copy the file to the pods
  echo "Copying $file_to_copy to $pod:$dest_path..."
  kubectl cp "$file_to_copy" "$namespace/$pod:$dest_path"
  if [ $? -ne 0 ]; then
    echo -e "${RED_TEXT}Error: Failed to copy $file_to_copy to $pod."
    continue
  fi

# Run the service_status command in the pod
  echo "checking status.... $service_status in $pod..."
  kubectl exec -n "$namespace" "$pod" -- bash -c "$service_status"
  if [ $? -ne 0 ]; then
    echo -e "${RED_TEXT}Error: Failed to restart service $service_status in $pod."
  else
    echo -e "Service $service_status restarted successfully in $pod${GREEN_TEXT}."
  fi

done

echo "Script execution completed."
