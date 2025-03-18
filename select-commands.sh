#!/bin/bash

# Color definitions for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Define deployment directory
DEPLOY_DIR="/home/devops_cloud/script/deploy"
FILE="ipshow.sh"

# Array of deploy files (using absolute paths)
deploy_files=(
  "$DEPLOY_DIR/cp_201_101/$FILE"
  "$DEPLOY_DIR/cp_202_101/$FILE"
  "$DEPLOY_DIR/cp_203_101/$FILE"
  "$DEPLOY_DIR/cp_204_101/$FILE"
  "$DEPLOY_DIR/cp_205_101/$FILE"
  "$DEPLOY_DIR/cp_206_101/$FILE"
  "$DEPLOY_DIR/cp_207_101/$FILE"
)

# Log file
LOG_FILE="$DEPLOY_DIR/deployment.log"

# Ensure log file exists
touch "$LOG_FILE"

# Function to execute a command across all deployment files
run_command_across_files() {
  local command="$1"
  echo -e "\n${YELLOW}🔹 Running command: $command${NC}"
  echo "$(date '+%Y-%m-%d %H:%M:%S') - Running command: $command" >> "$LOG_FILE"

  local valid_files=()
  
  # Collect only existing files
  for deploy_file in "${deploy_files[@]}"; do
    if [ -f "$deploy_file" ]; then
      valid_files+=("$deploy_file")
    else
      echo -e "${RED}⚠️ Warning: $deploy_file not found. Skipping...${NC}"
      echo "$(date '+%Y-%m-%d %H:%M:%S') - Warning: $deploy_file not found. Skipping..." >> "$LOG_FILE"
    fi
  done

  # Exit if no valid files found
  if [ ${#valid_files[@]} -eq 0 ]; then
    echo -e "${RED}❌ No valid deployment files found. Exiting.${NC}"
    exit 1
  fi

  for deploy_file in "${valid_files[@]}"; do
    echo -e "🔄 ${BLUE}Processing: $deploy_file${NC}"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Processing: $deploy_file" >> "$LOG_FILE"

    case "$command" in
      "bash")
        # Ensure the script is executable before running
        if [ ! -x "$deploy_file" ]; then
          chmod +x "$deploy_file"
        fi
        bash "$deploy_file" | tee -a "$LOG_FILE"
        ;;
      "grep -i show")
        grep -i "show" "$deploy_file" | tee -a "$LOG_FILE"
        ;;
      "cat")
        cat "$deploy_file" | tee -a "$LOG_FILE"
        ;;
      "log")
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Deployment logged for $deploy_file" | tee -a "$LOG_FILE"
        ;;
      *)
        echo -e "${RED}⚠️ Unknown command: $command${NC}"
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Error: Unknown command $command" >> "$LOG_FILE"
        ;;
    esac
  done
}

# Function to display menu and execute selected command
execute_selected_command() {
  while true; do
    printf "\n${BLUE}📌 Select a command to run:${NC}\n"
    printf "${YELLOW}1${NC} - Run scripts (execute each script)\n"
    printf "${YELLOW}2${NC} - Search for 'show' in scripts (grep -i show)\n"
    printf "${YELLOW}3${NC} - Display script contents (cat)\n"
    printf "${YELLOW}4${NC} - Log deployment\n"
    printf "${YELLOW}5${NC} - Exit\n"

    read -p "Enter option (1-5): " choice

    case "$choice" in
      1) run_command_across_files "bash" ;;
      2) run_command_across_files "grep -i show" ;;
      3) run_command_across_files "cat" ;;
      4) run_command_across_files "log" ;;
      5) echo -e "🚀 ${GREEN}Exiting script.${NC}"; exit 0 ;;
      *) echo -e "❌ ${RED}Invalid option. Please try again.${NC}" ;;
    esac
  done
}

# Start interactive execution
execute_selected_command
