# #!/bin/bash

# # # Define the release version
# # release_version="1.30.11"

# # Array of deploy files
# deploy_files=(
#   "deploy/cp_201_101"
#   "deploy/cp_202_101"
#   "deploy/cp_203_101"
#   "deploy/cp_204_101"
#   "deploy/cp_205_101"
#   "deploy/cp_206_101"
#   "deploy/cp_207_101"
# )

# # Loop through each deploy file and execute the command
# for deploy_file in "${deploy_files[@]}"; do
#   deploy --create "$release_version" -f "$deploy_file"
# done

# echo "Deployment commands executed for release version $release_version."



# #!/bin/bash

# # Define the release version
# release_version="1.30.11"

# # Define the list of deployment files
# deploy_files=(
#   "deploy/cp_201_101"
#   "deploy/cp_202_101"
#   "deploy/cp_203_101"
#   "deploy/cp_204_101"
#   "deploy/cp_205_101"
#   "deploy/cp_206_101"
#   "deploy/cp_207_101"
# )

# # Loop through each deployment file and execute the command
# for file in "${deploy_files[@]}"; do
#     echo "Executing: deploy --create $release_version -f $file"
#     deploy --create "$release_version" -f "$file"
# done

# echo "All deployments completed."


# #!/bin/bash

# deploy_files=(
#   "deploy/cp_201_101"
#   "deploy/cp_202_101"
#   "deploy/cp_203_101"
#   "deploy/cp_204_101"
#   "deploy/cp_205_101"
#   "deploy/cp_206_101"
#   "deploy/cp_207_101"
# )

# echo "Current Working Directory:"
# pwd

# for file in "${deploy_files[@]}"; do
#   echo "Checking file: $file"

#   if [ -f "$file" ]; then
#     echo "Reading content from: $file"
#     while IFS= read -r line; do
#       echo "$line"
#     done < "$file"
#   else
#     echo "File not found: $file"
#   fi
# done
