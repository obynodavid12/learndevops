#!/bin/bash
ACCOUNT_ID="<aws_account_id>"

# Create an IAM policy document with limited permissions
POLICY_DOCUMENT=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "eks:DeleteCluster",
                "eks:UpdateCluster",
                "iam:CreateRolePolicy",
                "iam:GetRole",
                "iam:PassRole",
                "iam:AttachRolePolicy",
                "iam:DetachRolePolicy",
                "logs:CreateLogGroup",
                "logs:CreateLogGroup",
                "s3:GetObject",
                "cloudformation:*"
            ],
            "Resource": "*"
        }
      ] 
}
EOF
)

# Create the IAM policy
aws iam create-policy --policy-name deployment-server-policy --policy-document "$POLICY_DOCUMENT"

# Create the IAM role
aws iam create-role --role-name deployment-server-role --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": {
        "Effect": "Allow",
        "Principal": {
            "Service": "ec2.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
    }
}'

# Attach the policy to the role
aws iam attach-role-policy --policy-arn "arn:aws:iam::$ACCOUNT_ID:policy/deployment-server-policy" --role-name deployment-server-role

echo "Deployment server role created successfully."
