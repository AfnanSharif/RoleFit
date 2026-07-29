targetScope = 'resourceGroup'

@description('Azure region for all RoleFit resources.')
param location string = resourceGroup().location

@minLength(2)
@maxLength(32)
@description('Container App name and resource-name prefix.')
param appName string = 'rolefit-studio'

@description('Fully qualified image, including registry and immutable tag.')
param image string

@description('Name of an existing Azure Container Registry in this resource group.')
param acrName string

@secure()
@description('Optional OpenAI API key. Leave empty for the local-only deployment.')
param openAiApiKey string = ''

@description('OpenAI model used by the optional feedback adapter.')
param openAiModel string = 'gpt-4o-mini'

@description('OpenAI embedding model used by the optional semantic adapter.')
param openAiEmbeddingModel string = 'text-embedding-3-small'

@minValue(0)
@maxValue(3)
param minReplicas int = 0

@minValue(1)
@maxValue(10)
param maxReplicas int = 3

var normalizedPrefix = toLower(replace(appName, '_', '-'))
var workspaceName = take('${normalizedPrefix}-logs-${uniqueString(resourceGroup().id)}', 63)
var environmentName = take('${normalizedPrefix}-env', 60)
var pullIdentityName = take('${normalizedPrefix}-acr-pull', 128)
var openAiSecrets = empty(openAiApiKey) ? [] : [
  {
    name: 'openai-api-key'
    value: openAiApiKey
  }
]
var openAiEnvironment = empty(openAiApiKey) ? [] : [
  {
    name: 'OPENAI_API_KEY'
    secretRef: 'openai-api-key'
  }
]

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: acrName
}

resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: workspaceName
  location: location
  properties: {
    retentionInDays: 30
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
  sku: {
    name: 'PerGB2018'
  }
}

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: environmentName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logs.properties.customerId
        sharedKey: logs.listKeys().primarySharedKey
      }
    }
  }
}

resource pullIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: pullIdentityName
  location: location
}

resource acrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, pullIdentity.id, 'rolefit-acr-pull')
  scope: registry
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      '7f951dda-4ed3-4680-a7ca-43fe172d538d'
    )
    principalId: pullIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: normalizedPrefix
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${pullIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        allowInsecure: false
        targetPort: 8000
        transport: 'auto'
      }
      registries: [
        {
          server: registry.properties.loginServer
          identity: pullIdentity.id
        }
      ]
      secrets: openAiSecrets
    }
    template: {
      containers: [
        {
          name: 'rolefit'
          image: image
          env: concat([
            {
              name: 'PORT'
              value: '8000'
            }
            {
              name: 'OPENAI_MODEL'
              value: openAiModel
            }
            {
              name: 'OPENAI_EMBEDDING_MODEL'
              value: openAiEmbeddingModel
            }
          ], openAiEnvironment)
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          probes: [
            {
              type: 'Startup'
              httpGet: {
                path: '/_stcore/health'
                port: 8000
                scheme: 'HTTP'
              }
              initialDelaySeconds: 5
              periodSeconds: 5
              failureThreshold: 18
            }
            {
              type: 'Liveness'
              httpGet: {
                path: '/_stcore/health'
                port: 8000
                scheme: 'HTTP'
              }
              periodSeconds: 30
              failureThreshold: 3
            }
          ]
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        rules: [
          {
            name: 'http-concurrency'
            http: {
              metadata: {
                concurrentRequests: '20'
              }
            }
          }
        ]
      }
    }
  }
  dependsOn: [
    acrPull
  ]
}

output applicationUrl string = 'https://${app.properties.configuration.ingress.fqdn}'
output containerAppName string = app.name
output containerAppEnvironment string = environment.name
output openAiEnabled bool = !empty(openAiApiKey)
