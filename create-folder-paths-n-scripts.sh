# #!/bin/bash

# # Define the main directory and subdirectories
# MAIN_DIR="/home/devops_cloud/script/file-mgt/project_structure"
# PATH1="$MAIN_DIR/path1"
# PATH2="$MAIN_DIR/path2"

# # Create the directory structure
# mkdir -p "$PATH1"
# mkdir -p "$PATH2"

# # Create the first bash script in path1
# cat > "$PATH1/script1.sh" << 'EOF'
# #!/bin/bash
# # This is script1 in path1

# echo "Running script1 from path1"
# echo "Current directory: $(pwd)"
# echo "This script can perform path1-specific operations"

# # Example function
# path1_function() {
#     echo "Processing data in path1..."
#     # Add your path1-specific commands here
# }

# # Call the function
# path1_function
# EOF

# # Create the second bash script in path1
# cat > "$PATH1/script2.sh" << 'EOF'
# #!/bin/bash
# # This is script2 in path1

# echo "Running script2 from path1"
# echo "Current time: $(date)"
# echo "This script handles secondary operations for path1"

# # Example loop
# for i in {1..3}; do
#     echo "Path1 processing step $i"
#     sleep 1
# done
# EOF

# # Create the first bash script in path2
# cat > "$PATH2/script1.sh" << 'EOF'
# #!/bin/bash
# # This is script1 in path2

# echo "Running script1 from path2"
# echo "Hostname: $(hostname)"
# echo "This script performs path2-specific operations"

# # Example conditional
# if [ -f "/etc/os-release" ]; then
#     echo "OS details:"
#     cat /etc/os-release | grep PRETTY_NAME
# else
#     echo "OS details not available"
# fi
# EOF

# # Create the second bash script in path2
# cat > "$PATH2/script2.sh" << 'EOF'
# #!/bin/bash
# # This is script2 in path2

# echo "Running script2 from path2"
# echo "User: $(whoami)"
# echo "This script handles monitoring tasks for path2"

# # Example monitoring function
# check_system() {
#     echo "Memory usage:"
#     free -h | head -2
    
#     echo "Disk usage:"
#     df -h | head -2
# }

# # Run the check
# check_system
# EOF

# # Make all scripts executable
# chmod +x "$PATH1"/*.sh
# chmod +x "$PATH2"/*.sh

# echo "Directory structure created successfully!"
# echo "├── $MAIN_DIR"
# echo "│   ├── path1"
# echo "│   │   ├── script1.sh"
# echo "│   │   └── script2.sh"
# echo "│   └── path2"
# echo "│       ├── script1.sh"
# echo "│       └── script2.sh"
# echo ""
# echo "All scripts are now executable. You can run them with:"
# echo "bash $PATH1/script1.sh"
# echo "bash $PATH2/script1.sh"
# echo "Or directly if you're in their directory:"
# echo "cd $PATH1 && ./script1.sh"


# #!/bin/bash
# mkdir -p parent/{folder1,folder2}

# cat > parent/folder1/script1.sh << 'EOF'
# #!/bin/bash
# echo "This is script1 in folder1"  
# EOF

# cat > parent/folder2/script2.sh << 'EOF'
# #!/bin/bash
# echo "This is script2 in folder2"
# EOF

# chmod +x parent/folder1/script1.sh parent/folder2/script2.sh


#!/bin/bash

cd ~/projects               # Navigate to the desired parent directory
mkdir folder1 folder2       # Create the two folders
echo -e '#!/bin/bash\n\necho "This is script 1"' > folder1/script1.sh  # Create script 1
chmod +x folder1/script1.sh  # Make script 1 executable
echo -e '#!/bin/bash\n\necho "This is script 2"' > folder2/script2.sh  # Create script 2
chmod +x folder2/script2.sh  # Make script 2 executable
