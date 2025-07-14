I’ll create a GitHub Actions workflow that uses a workflow dispatch to select a folder containing JSON files, retrieves a Kubernetes secret for an API token, and makes API calls (DELETE, CREATE, or UPDATE) using those JSON files. The workflow will allow you to specify the folder and operation type via inputs.

Assumptions
JSON files are stored in the repository under a specified folder (e.g., configs/ or a user-selected folder).

Each JSON file contains the payload for an API call.

The API endpoint supports DELETE, POST (for CREATE), and PUT (for UPDATE) requests.

The Kubernetes secret contains an API token used for authentication.

The folder structure and JSON files are valid and accessible in the repository.

GitHub Actions Workflow
name: Manage API Resources with Kubernetes Secret

on:
  workflow_dispatch:
    inputs:
      folder:
        description: 'Path to the folder containing JSON files (relative to repository root)'
        required: true
        type: string
      operation:
        description: 'API operation to perform (CREATE, UPDATE, DELETE)'
        required: true
        type: choice
        options:
          - CREATE
          - UPDATE
          - DELETE

jobs:
  manage-api-resources:
    runs-on: ubuntu-latest
    permissions:
      contents: read

    steps:
      # Checkout the repository code
      - name: Checkout code
        uses: actions/checkout@v4

      # Set up kubectl
      - name: Set up kubectl
        uses: azure/setup-kubectl@v3
        with:
          version: 'latest'

      # Configure Kubernetes cluster access
      - name: Configure Kubernetes context
        env:
          KUBE_CONFIG: ${{ secrets.KUBE_CONFIG }}
        run: |
          mkdir -p $HOME/.kube
          echo "$KUBE_CONFIG" > $HOME/.kube/config
          chmod 600 $HOME/.kube/config

      # Retrieve API token from Kubernetes secret
      - name: Retrieve API token from Kubernetes secret
        env:
          NAMESPACE: your-namespace  # Replace with your namespace
          SECRET_NAME: your-secret-name  # Replace with your secret name
          SECRET_KEY: token  # The key in the secret containing the API token
        run: |
          TOKEN=$(kubectl get secret $SECRET_NAME -n $NAMESPACE -o jsonpath="{.data.$SECRET_KEY}" | base64 -d)
          if [ -z "$TOKEN" ]; then
            echo "Error: Failed to retrieve token from secret" >&2
            exit 1
          fi
          echo "API_TOKEN=$TOKEN" >> $GITHUB_ENV

      # Process JSON files and make API calls
      - name: Process JSON files and make API calls
        env:
          API_ENDPOINT: https://api.example.com/endpoint  # Replace with your API endpoint
          FOLDER_PATH: ${{ github.event.inputs.folder }}
          OPERATION: ${{ github.event.inputs.operation }}
        run: |
          # Validate folder path
          if [ ! -d "$FOLDER_PATH" ]; then
            echo "Error: Folder $FOLDER_PATH does not exist" >&2
            exit 1
          fi

          # Determine HTTP method based on operation
          case "$OPERATION" in
            CREATE)
              HTTP_METHOD="POST"
              ;;
            UPDATE)
              HTTP_METHOD="PUT"
              ;;
            DELETE)
              HTTP_METHOD="DELETE"
              ;;
            *)
              echo "Error: Invalid operation $OPERATION" >&2
              exit 1
              ;;
          esac

          # Process each JSON file in the folder
          for file in "$FOLDER_PATH"/*.json; do
            if [ -f "$file" ]; then
              echo "Processing $file..."
              # Make API call with the JSON file
              RESPONSE=$(curl -s -w "%{http_code}" -X $HTTP_METHOD \
                -H "Authorization: Bearer $API_TOKEN" \
                -H "Content-Type: application/json" \
                --data @"$file" \
                "$API_ENDPOINT")
              
              # Extract HTTP status code (last 3 characters)
              STATUS=${RESPONSE: -3}
              BODY=${RESPONSE%???}
              
              if [ "$STATUS" -ge 200 ] && [ "$STATUS" -lt 300 ]; then
                echo "Successfully performed $OPERATION on $file (Status: $STATUS)"
                echo "$BODY"
              else
                echo "Error: Failed to perform $OPERATION on $file (Status: $STATUS)" >&2
                echo "$BODY" >&2
                exit 1
              fi
            else
              echo "No JSON files found in $FOLDER_PATH" >&2
              exit 1
            fi
          done
How It Works
Workflow Dispatch:

The workflow is triggered manually via workflow_dispatch.

It accepts two inputs:

folder: The path to the folder containing JSON files (e.g., configs/ or data/resources/).

operation: The API operation to perform (CREATE, UPDATE, or DELETE).

Steps:

Checkout code: Clones the repository to access the JSON files.

Set up kubectl: Installs kubectl to interact with the Kubernetes cluster.

Configure Kubernetes context: Sets up the Kubernetes configuration using the KUBE_CONFIG secret.

Retrieve API token: Fetches the API token from the specified Kubernetes secret and stores it in API_TOKEN.

Process JSON files:

Validates the provided folder path.

Maps the operation to an HTTP method (POST for CREATE, PUT for UPDATE, DELETE for DELETE).

Iterates through all .json files in the specified folder.

For each JSON file, makes an API call using curl with the appropriate HTTP method, token, and JSON payload.

Checks the HTTP status code to determine success (200–299) or failure, logging the response body.

Error Handling:

Checks if the folder exists and contains JSON files.

Validates the operation input.

Ensures the token is retrieved successfully.

Verifies API call success based on HTTP status codes.

Exits with an error code if any step fails, providing detailed error messages.

Prerequisites
Kubernetes Secret:

Ensure a secret exists in your Kubernetes cluster, e.g.:

kubectl create secret generic your-secret-name --from-literal=token=your-api-token -n your-namespace
Update NAMESPACE, SECRET_NAME, and SECRET_KEY in the workflow to match your setup.

Kubernetes Configuration:

Store your Kubernetes config file as a GitHub secret named KUBE_CONFIG.

Go to your repository → Settings → Secrets and variables → Actions → New repository secret, and add KUBE_CONFIG.

JSON Files:

Store JSON files in a folder in your repository (e.g., configs/).

Example JSON file (configs/resource1.json):

{
  "name": "resource1",
  "value": "example"
}
Ensure the JSON files are formatted correctly for your API.

API Endpoint:

Replace https://api.example.com/endpoint with your actual API endpoint.

Ensure the endpoint supports the expected HTTP methods (POST, PUT, DELETE) and accepts JSON payloads.

Running the Workflow
Add the Workflow:

Save the workflow as .github/workflows/manage-api-resources.yml in your repository.

Trigger the Workflow:

Go to the “Actions” tab in your GitHub repository.

Select the “Manage API Resources with Kubernetes Secret” workflow.

Click “Run workflow” and provide:

folder: The path to the folder (e.g., configs/).

operation: Choose CREATE, UPDATE, or DELETE.

Click “Run workflow” to start the process.

Monitor Logs:

Check the workflow logs in the “Actions” tab to see the results of each API call, including success/failure messages and response bodies.

Example JSON Files
Assume your repository has a folder configs/ with the following files:

configs/resource1.json:

{
  "id": "resource1",
  "name": "Resource One",
  "data": "example data"
}
configs/resource2.json:

{
  "id": "resource2",
  "name": "Resource Two",
  "data": "test data"
}
If you run the workflow with folder: configs and operation: CREATE, it will send a POST request for each JSON file to the API endpoint.

Customization
Dynamic API Endpoint: If the endpoint varies per JSON file, include it in the JSON file (e.g., "endpoint": "https://api.example.com/resource1") and modify the script to extract it:

ENDPOINT=$(jq -r '.endpoint' "$file")
curl -X $HTTP_METHOD -H "Authorization: Bearer $API_TOKEN" -H "Content-Type: application/json" --data @"$file" "$ENDPOINT"
Batch Processing: Add a step to validate JSON files before processing (e.g., using jq to check syntax).

Custom Headers: Add additional headers to the curl command if required by your API.

Error Retry: Implement a retry mechanism for failed API calls:

for attempt in {1..3}; do
  RESPONSE=$(curl -s -w "%{http_code}" ...)
  STATUS=${RESPONSE: -3}
  [ "$STATUS" -ge 200 ] && [ "$STATUS" -lt 300 ] && break
  echo "Retry $attempt failed for $file" >&2
  sleep 2
done
Multiple Operations: Allow processing multiple operations in a single run by modifying the workflow to accept a list of operations or process different folders for different operations.

Security Considerations
Secret Security: Ensure KUBE_CONFIG and the API token are not logged or exposed. Restrict access to the KUBE_CONFIG secret in GitHub.

Minimal Permissions: The Kubernetes service account in KUBE_CONFIG should have read-only access to the specific secret.

Input Validation: The workflow validates the folder and operation, but you may want to add stricter checks (e.g., ensure the folder path doesn’t access sensitive areas).

API Token Scope: Ensure the API token has the minimum necessary permissions for the CREATE/UPDATE/DELETE operations.

If you need specific modifications (e.g., a different API endpoint structure, custom JSON parsing, or additional error handling), let me know, and I can tailor the workflow further!

