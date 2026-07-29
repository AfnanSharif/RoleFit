#!/usr/bin/env bash
set -Eeuo pipefail

required=(AZURE_SUBSCRIPTION_ID AZURE_RESOURCE_GROUP AZURE_LOCATION AZURE_ACR_NAME)
for variable in "${required[@]}"; do
  if [[ -z "${!variable:-}" ]]; then
    echo "Missing required environment variable: ${variable}" >&2
    exit 2
  fi
done

command -v az >/dev/null || { echo "Azure CLI (az) is required." >&2; exit 2; }
az account show >/dev/null
az account set --subscription "${AZURE_SUBSCRIPTION_ID}"

app_name="${AZURE_APP_NAME:-rolefit-studio}"
image_tag="${IMAGE_TAG:-$(git rev-parse --short HEAD 2>/dev/null || printf 'manual')}"
openai_model="${OPENAI_MODEL:-gpt-4o-mini}"
embedding_model="${OPENAI_EMBEDDING_MODEL:-text-embedding-3-small}"

for provider in Microsoft.App Microsoft.OperationalInsights Microsoft.ManagedIdentity Microsoft.ContainerRegistry; do
  az provider register --namespace "${provider}" --wait
done

az group create \
  --name "${AZURE_RESOURCE_GROUP}" \
  --location "${AZURE_LOCATION}" \
  --tags application=rolefit-studio managed-by=bicep

if ! az acr show --name "${AZURE_ACR_NAME}" --resource-group "${AZURE_RESOURCE_GROUP}" >/dev/null 2>&1; then
  az acr create \
    --name "${AZURE_ACR_NAME}" \
    --resource-group "${AZURE_RESOURCE_GROUP}" \
    --location "${AZURE_LOCATION}" \
    --sku Basic \
    --admin-enabled false
fi

az acr build \
  --registry "${AZURE_ACR_NAME}" \
  --image "rolefit-studio:${image_tag}" \
  --build-arg REQUIREMENTS_FILE=requirements-cloud.txt \
  .

login_server="$(az acr show --name "${AZURE_ACR_NAME}" --query loginServer --output tsv)"
deployment="$(az deployment group create \
  --resource-group "${AZURE_RESOURCE_GROUP}" \
  --name "rolefit-${image_tag}" \
  --template-file deploy/azure/main.bicep \
  --parameters \
    location="${AZURE_LOCATION}" \
    appName="${app_name}" \
    acrName="${AZURE_ACR_NAME}" \
    image="${login_server}/rolefit-studio:${image_tag}" \
    openAiApiKey="${OPENAI_API_KEY:-}" \
    openAiModel="${openai_model}" \
    openAiEmbeddingModel="${embedding_model}" \
  --query properties.outputs.applicationUrl.value \
  --output tsv)"

echo "RoleFit Studio is available at ${deployment}"
