#!/usr/bin/env bash
set -euo pipefail

# === CONFIGURABLE VARIABLES ===
VPC_ID="vpc-0558ee04b4bc3ff4c"
REGION="us-east-1"
NEW_VPC_CIDR="172.32.65.0/24"              # CIDR to add to the VPC
SOURCE_ROUTE_TABLE_ID="rtb-0e52c9377892f5406" # Copy routes from this table
TAG_PREFIX="use1-vpc Primary"

# Define your two subnet CIDRs here
SUBNET_1_CIDR="172.32.65.0/26"
SUBNET_2_CIDR="172.32.65.64/26"

# Optional: Specify AZs for each subnet (leave empty for automatic round-robin)
SUBNET_1_AZ=""  # e.g., "us-east-1a" or leave empty
SUBNET_2_AZ=""  # e.g., "us-east-1b" or leave empty

# === FUNCTION DEFINITIONS ===

# 1. Check and add new CIDR to existing VPC
add_vpc_cidr() {
  echo "🟢 Checking VPC CIDR configuration for $VPC_ID ..."
  
  # Get all existing CIDRs with their states
  echo ""
  echo "Current VPC CIDR blocks:"
  aws ec2 describe-vpcs --vpc-ids "$VPC_ID" --region "$REGION" \
    --query 'Vpcs[0].CidrBlockAssociationSet[].[CidrBlock,CidrBlockState.State]' \
    --output table
  echo ""
  
  # Check if CIDR is already associated
  EXISTING_CIDRS=$(aws ec2 describe-vpcs --vpc-ids "$VPC_ID" --region "$REGION" \
    --query 'Vpcs[0].CidrBlockAssociationSet[].CidrBlock' --output text)
  
  if echo "$EXISTING_CIDRS" | grep -q "$NEW_VPC_CIDR"; then
    echo "ℹ️  CIDR $NEW_VPC_CIDR already associated with VPC $VPC_ID"
    
    # Verify it's in associated state
    STATE=$(aws ec2 describe-vpcs --vpc-ids "$VPC_ID" --region "$REGION" \
      --query "Vpcs[0].CidrBlockAssociationSet[?CidrBlock=='$NEW_VPC_CIDR'].CidrBlockState.State" \
      --output text)
    
    if [[ "$STATE" != "associated" ]]; then
      echo "⚠️  Warning: CIDR state is '$STATE', waiting for 'associated' state..."
      wait_for_cidr_association
    else
      echo "✅ CIDR is already in 'associated' state"
    fi
    return 0
  fi
  
  echo "🔄 Adding new CIDR $NEW_VPC_CIDR to VPC..."
  aws ec2 associate-vpc-cidr-block \
    --vpc-id "$VPC_ID" \
    --cidr-block "$NEW_VPC_CIDR" \
    --region "$REGION" \
    >/dev/null
  
  echo "✅ VPC CIDR association initiated"
  wait_for_cidr_association
}

# 1b. Wait for CIDR association to complete
wait_for_cidr_association() {
  echo "⏳ Waiting for CIDR $NEW_VPC_CIDR association to complete..."
  
  for i in {1..60}; do
    STATE=$(aws ec2 describe-vpcs --vpc-ids "$VPC_ID" --region "$REGION" \
      --query "Vpcs[0].CidrBlockAssociationSet[?CidrBlock=='$NEW_VPC_CIDR'].CidrBlockState.State" \
      --output text 2>/dev/null || echo "unknown")
    
    if [[ "$STATE" == "associated" ]]; then
      echo "✅ CIDR association complete (state: $STATE)"
      echo "⏳ Waiting additional 10 seconds for full propagation..."
      sleep 10
      return 0
    fi
    
    if [[ "$STATE" == "failed" || "$STATE" == "failing" ]]; then
      echo "❌ Error: CIDR association failed with state: $STATE"
      exit 1
    fi
    
    if (( i % 6 == 0 )); then  # Print every 30 seconds
      echo "   Still waiting... (attempt $i/60, current state: $STATE)"
    fi
    sleep 5
  done
  
  echo "❌ Error: Timeout waiting for CIDR association to complete"
  exit 1
}

# 2. Validate CIDR format and check if it's within VPC CIDR
validate_cidr() {
  local cidr=$1
  local context=$2
  
  if ! python3 -c "from ipaddress import ip_network; ip_network('$cidr')" 2>/dev/null; then
    echo "❌ Error: Invalid CIDR format: $cidr"
    exit 1
  fi
  
  # Additional validation: check if subnet CIDR is within VPC CIDR
  if [[ "$context" == "subnet" ]]; then
    python3 - "$cidr" "$NEW_VPC_CIDR" <<'PYCODE'
import sys
from ipaddress import ip_network

subnet = ip_network(sys.argv[1])
vpc = ip_network(sys.argv[2])

if not subnet.subnet_of(vpc):
    print(f"❌ Error: Subnet CIDR {subnet} is not within VPC CIDR {vpc}")
    sys.exit(1)
PYCODE
    if [[ $? -ne 0 ]]; then
      exit 1
    fi
  fi
}

# 3. Get available AZs
get_availability_zones() {
  aws ec2 describe-availability-zones --region "$REGION" \
    --query 'AvailabilityZones[].ZoneName' --output text
}

# 4. Create a single subnet with route table
create_subnet_with_routes() {
  local CIDR=$1
  local AZ=$2
  local INDEX=$3
  local SUBNET_NAME="${TAG_PREFIX} Private Subnet (AZ${INDEX})"
  local RTB_NAME="${TAG_PREFIX} Private Routes (AZ${INDEX})"

  echo ""
  echo "========================================="
  echo "➡️  Creating Subnet $INDEX"
  echo "    CIDR: $CIDR"
  echo "    AZ: $AZ"
  echo "========================================="
  
  # Double-check VPC CIDR one more time before creating subnet
  echo "🔍 Verifying VPC CIDR state before subnet creation..."
  VPC_STATE=$(aws ec2 describe-vpcs --vpc-ids "$VPC_ID" --region "$REGION" \
    --query "Vpcs[0].CidrBlockAssociationSet[?CidrBlock=='$NEW_VPC_CIDR'].CidrBlockState.State" \
    --output text)
  
  if [[ "$VPC_STATE" != "associated" ]]; then
    echo "❌ Error: VPC CIDR $NEW_VPC_CIDR is in state '$VPC_STATE', not 'associated'"
    echo "Cannot create subnet until VPC CIDR is fully associated."
    exit 1
  fi
  echo "✅ VPC CIDR is associated"
  
  # Verify subnet CIDR is within VPC CIDR
  echo "🔍 Verifying subnet CIDR is within VPC CIDR..."
  python3 - "$CIDR" "$NEW_VPC_CIDR" <<'PYCODE'
import sys
from ipaddress import ip_network

subnet = ip_network(sys.argv[1])
vpc = ip_network(sys.argv[2])

print(f"  Subnet: {subnet}")
print(f"  VPC:    {vpc}")

if not subnet.subnet_of(vpc):
    print(f"❌ Error: Subnet CIDR {subnet} is NOT within VPC CIDR {vpc}")
    sys.exit(1)
else:
    print(f"✅ Subnet CIDR is within VPC CIDR")
PYCODE
  
  if [[ $? -ne 0 ]]; then
    exit 1
  fi
  
  # Check if subnet already exists with this CIDR
  EXISTING_SUBNET=$(aws ec2 describe-subnets --region "$REGION" \
    --filters "Name=vpc-id,Values=$VPC_ID" "Name=cidr-block,Values=$CIDR" \
    --query 'Subnets[0].SubnetId' --output text 2>/dev/null || echo "None")
  
  if [[ "$EXISTING_SUBNET" != "None" && -n "$EXISTING_SUBNET" ]]; then
    echo "ℹ️  Subnet with CIDR $CIDR already exists: $EXISTING_SUBNET"
    SUBNET_ID="$EXISTING_SUBNET"
  else
    echo "🔨 Creating subnet..."
    SUBNET_ID=$(aws ec2 create-subnet \
      --vpc-id "$VPC_ID" \
      --cidr-block "$CIDR" \
      --availability-zone "$AZ" \
      --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=${SUBNET_NAME}}]" \
      --region "$REGION" \
      --query 'Subnet.SubnetId' --output text 2>&1)
    
    if [[ $? -ne 0 ]]; then
      echo "❌ Error creating subnet:"
      echo "$SUBNET_ID"
      exit 1
    fi
    echo "✅ Created Subnet: $SUBNET_ID"
  fi

  # Create route table
  RTB_ID=$(aws ec2 create-route-table \
    --vpc-id "$VPC_ID" \
    --tag-specifications "ResourceType=route-table,Tags=[{Key=Name,Value=${RTB_NAME}}]" \
    --region "$REGION" \
    --query 'RouteTable.RouteTableId' --output text)

  echo "   ✅ Created Route Table: $RTB_ID"

  # Get current route table associations for this subnet
  CURRENT_ASSOC=$(aws ec2 describe-route-tables --region "$REGION" \
    --filters "Name=association.subnet-id,Values=$SUBNET_ID" \
    --query 'RouteTables[0].Associations[?SubnetId==`'$SUBNET_ID'`].RouteTableAssociationId' \
    --output text)

  # Disassociate old route table if exists
  if [[ -n "$CURRENT_ASSOC" && "$CURRENT_ASSOC" != "None" ]]; then
    echo "   🔄 Replacing existing route table association..."
    aws ec2 replace-route-table-association \
      --association-id "$CURRENT_ASSOC" \
      --route-table-id "$RTB_ID" \
      --region "$REGION" >/dev/null
  else
    # Associate new route table with subnet
    aws ec2 associate-route-table \
      --route-table-id "$RTB_ID" \
      --subnet-id "$SUBNET_ID" \
      --region "$REGION" >/dev/null
  fi

  echo "   🔗 Associated Route Table with Subnet"

  # Copy routes from source table
  copy_routes "$SOURCE_ROUTE_TABLE_ID" "$RTB_ID"
  
  echo "   ✅ Subnet $SUBNET_ID configured successfully"
}

# 5. Copy routes from existing route table
copy_routes() {
  SRC_RTB=$1
  DEST_RTB=$2
  echo "   📡 Copying routes from $SRC_RTB → $DEST_RTB ..."
  
  ROUTES=$(aws ec2 describe-route-tables --route-table-ids "$SRC_RTB" --region "$REGION" \
    --query 'RouteTables[0].Routes[]' --output json)

  ROUTE_COUNT=0
  echo "$ROUTES" | jq -c '.[]' | while read -r route; do
    # Get destination CIDR (could be IPv4 or IPv6)
    DEST=$(echo "$route" | jq -r '.DestinationCidrBlock // empty')
    DEST_IPV6=$(echo "$route" | jq -r '.DestinationIpv6CidrBlock // empty')
    
    # Get only the route targets we want to copy
    GATEWAY=$(echo "$route" | jq -r '.GatewayId // empty')
    NATGW=$(echo "$route" | jq -r '.NatGatewayId // empty')
    VPCPEER=$(echo "$route" | jq -r '.VpcPeeringConnectionId // empty')
    VGW=$(echo "$route" | jq -r '.VirtualGatewayId // empty')
    VPCE=$(echo "$route" | jq -r '.VpcEndpointId // empty')

    # Determine which destination to use
    if [[ -n "$DEST" && "$DEST" != "null" ]]; then
      DESTINATION="$DEST"
      DEST_FLAG="--destination-cidr-block"
    elif [[ -n "$DEST_IPV6" && "$DEST_IPV6" != "null" ]]; then
      DESTINATION="$DEST_IPV6"
      DEST_FLAG="--destination-ipv6-cidr-block"
    else
      continue
    fi

    # Skip local routes
    if [[ "$DESTINATION" == "local" ]]; then
      continue
    fi

    # Build the create-route command with destination
    CMD=(aws ec2 create-route --route-table-id "$DEST_RTB" "$DEST_FLAG" "$DESTINATION" --region "$REGION")
    
    # Add the appropriate target - ONLY IGW, NAT GW, VGW, Peering, and VPC Endpoints
    TARGET_FOUND=false
    TARGET_NAME=""
    
    if [[ -n "$GATEWAY" && "$GATEWAY" != "null" ]]; then
      # Check if it's an IGW (starts with igw-) or VGW (starts with vgw-)
      if [[ "$GATEWAY" == igw-* ]]; then
        CMD+=(--gateway-id "$GATEWAY")
        TARGET_FOUND=true
        TARGET_NAME="IGW: $GATEWAY"
      elif [[ "$GATEWAY" == vgw-* ]]; then
        CMD+=(--gateway-id "$GATEWAY")
        TARGET_FOUND=true
        TARGET_NAME="VGW: $GATEWAY"
      fi
    elif [[ -n "$NATGW" && "$NATGW" != "null" ]]; then
      CMD+=(--nat-gateway-id "$NATGW")
      TARGET_FOUND=true
      TARGET_NAME="NAT GW: $NATGW"
    elif [[ -n "$VPCPEER" && "$VPCPEER" != "null" ]]; then
      CMD+=(--vpc-peering-connection-id "$VPCPEER")
      TARGET_FOUND=true
      TARGET_NAME="Peering: $VPCPEER"
    elif [[ -n "$VPCE" && "$VPCE" != "null" ]]; then
      CMD+=(--vpc-endpoint-id "$VPCE")
      TARGET_FOUND=true
      TARGET_NAME="VPC Endpoint: $VPCE"
    fi

    # Skip routes that don't match our allowed targets
    if [[ "$TARGET_FOUND" == false ]]; then
      echo "      ⏭️  Skipping route $DESTINATION (target not in allowed list)"
      continue
    fi

    # Execute the command
    if "${CMD[@]}" >/dev/null 2>&1; then
      echo "      ✅ Copied route: $DESTINATION → $TARGET_NAME"
      ((ROUTE_COUNT++)) || true
    else
      echo "      ⚠️  Failed to copy route: $DESTINATION → $TARGET_NAME (may already exist)"
    fi
  done
}

# === MAIN EXECUTION ===
main() {
  echo "========================================="
  echo "  VPC Two-Subnet Creator"
  echo "========================================="
  echo "VPC ID: $VPC_ID"
  echo "Region: $REGION"
  echo "New VPC CIDR: $NEW_VPC_CIDR"
  echo "Subnet 1 CIDR: $SUBNET_1_CIDR"
  echo "Subnet 2 CIDR: $SUBNET_2_CIDR"
  echo "Source Route Table: $SOURCE_ROUTE_TABLE_ID"
  echo "========================================="
  echo ""

  # Validate CIDR formats
  echo "🔍 Validating CIDR formats..."
  validate_cidr "$NEW_VPC_CIDR" "vpc"
  validate_cidr "$SUBNET_1_CIDR" "subnet"
  validate_cidr "$SUBNET_2_CIDR" "subnet"
  echo "✅ All CIDRs are valid and subnets are within VPC CIDR"
  echo ""

  # Add VPC CIDR
  add_vpc_cidr
  echo ""

  # Get available AZs
  AZS=($(get_availability_zones))
  echo "📍 Available AZs: ${AZS[*]}"
  echo ""

  # Determine AZs for subnets
  if [[ -z "$SUBNET_1_AZ" ]]; then
    SUBNET_1_AZ="${AZS[0]}"
    echo "ℹ️  Auto-selected AZ for Subnet 1: $SUBNET_1_AZ"
  fi

  if [[ -z "$SUBNET_2_AZ" ]]; then
    SUBNET_2_AZ="${AZS[1]}"
    echo "ℹ️  Auto-selected AZ for Subnet 2: $SUBNET_2_AZ"
  fi
  echo ""

  # Create subnets
  echo "📦 Creating subnets and route tables..."
  create_subnet_with_routes "$SUBNET_1_CIDR" "$SUBNET_1_AZ" "1"
  create_subnet_with_routes "$SUBNET_2_CIDR" "$SUBNET_2_AZ" "2"

  echo ""
  echo "========================================="
  echo "🎯 Both subnets created successfully!"
  echo "========================================="
  echo ""
  echo "Summary:"
  echo "  Subnet 1: $SUBNET_1_CIDR in $SUBNET_1_AZ"
  echo "  Subnet 2: $SUBNET_2_CIDR in $SUBNET_2_AZ"
  echo "========================================="
}

# Run main function
main
