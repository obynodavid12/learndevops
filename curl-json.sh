#!/bin/bash

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Define the output file
output_file="status.txt"

# Check if curl.json exists
if [[ ! -f curl.json ]]; then
  echo -e "${RED}Error: curl.json file not found!${NC}"
  exit 1
fi

# Process the JSON file and save the output
grep -E '"(id|employee_name|employee_salary|employee_age)":' curl.json | 
awk -F': ' '
  BEGIN { OFS="\t" }
  /"id":/            { id = $2 } 
  /"employee_name":/ { name = $2 } 
  /"employee_salary":/ { salary = $2 } 
  /"employee_age":/  { age = $2; print id, name, salary, age }
' | tr -d '",' > "$output_file"

# Print status message
echo -e "${GREEN}✓ Status information saved to $output_file${NC}"
echo -e "${YELLOW}...${NC}"

# grep -E '"(id|employee_name|employee_salary|employee_age)":' curl.json | 
# awk -F': ' '
#   BEGIN { OFS="\t" }
#   /"id":/            { id = $2 } 
#   /"employee_name":/ { name = $2 } 
#   /"employee_salary":/ { salary = $2 } 
#   /"employee_age":/  { age = $2; print id, name, salary, age }
# ' | tr -d '",' > status.txt


# grep -E '"(id|employee_name|employee_salary|employee_age)":' curl.json | 
# awk -F': ' '
#   /"id":/            { id = $2 } 
#   /"employee_name":/ { name = $2 } 
#   /"employee_salary":/ { salary = $2 } 
#   /"employee_age":/  { 
#     gsub(/[",]/, "", id); 
#     gsub(/"/, "", name); 
#     gsub(/,/, "", salary); 
#     print "id=" id " employee_name=" name " employee_salary=" salary " employee_age=" $2 
#   }' | tr -d '",' > status.txt

# jq -r '.data[] | [.id, .employee_name, .employee_salary, .employee_age] | join(": ")' curl.json > status.txt


# jq -r '.data[] | "id=\(.id) employee_name=\"\(.employee_name)\" employee_salary=\(.employee_salary) employee_age=\(.employee_age)"' curl.json > status.txt


# jq -r '.data[] | "id=\(.id) employee_name=\"\(.employee_name)\" employee_salary=\(.employee_salary) employee_age=\(.employee_age)"' curl.json > status.txt

# jq -r '.data[] | "id=" + (.id|tostring) + " employee_name=\"" + .employee_name + "\" employee_salary=" + (.employee_salary|tostring) + " employee_age=" + (.employee_age|tostring)' curl.json > status.txt

# # if jq isn't available, you could use a combination of grep and sed:
# grep -E '"id":|"employee_name":|"employee_salary":|"employee_age":' curl.json | \
# sed -E 's/"id": ([0-9]+),?/id=\1 /g; s/"employee_name": "([^"]+)",?/employee_name="\1" /g; s/"employee_salary": ([0-9]+),?/employee_salary=\1 /g; s/"employee_age": ([0-9]+),?/employee_age=\1\n/g' > status.txt


