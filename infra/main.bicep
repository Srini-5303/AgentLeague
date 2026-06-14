// Eldervale infrastructure — provisions the REAL Azure resources the GM needs.
// NOTE: Foundry agents are NOT an ARM resource — there is no Microsoft.AI/agents.
// Create the Foundry project + model deployments in the portal, then register
// optional named agents with infra/deploy_agents.py. This file provisions Cosmos,
// ACR, App Insights, the Container Apps environment, and the GM Container App.
//
// Deploy:  az deployment group create -g <rg> -f infra/main.bicep -p namePrefix=eldervale

@description('Prefix for resource names')
param namePrefix string = 'eldervale'

@description('Location for all resources')
param location string = resourceGroup().location

@description('Container image for the GM orchestrator (in ACR), e.g. <acr>.azurecr.io/eldervale-gm:latest')
param gmImage string = ''

@description('Foundry project endpoint (from the portal)')
param foundryProjectEndpoint string = ''

var cosmosName = '${namePrefix}-cosmos'
var acrName = toLower(replace('${namePrefix}acr', '-', ''))
var logName = '${namePrefix}-logs'
var aiName = '${namePrefix}-appinsights'
var caeName = '${namePrefix}-cae'
var appName = '${namePrefix}-gm'

// ── Cosmos DB (NoSQL, serverless) ─────────────────────────────────────────
resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' = {
  name: cosmosName
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    capabilities: [ { name: 'EnableServerless' } ]
    locations: [ { locationName: location, failoverPriority: 0 } ]
    consistencyPolicy: { defaultConsistencyLevel: 'Session' }
  }
}

resource cosmosDb 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-05-15' = {
  parent: cosmos
  name: 'fantasy-rpg'
  properties: { resource: { id: 'fantasy-rpg' } }
}

resource usersContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = {
  parent: cosmosDb
  name: 'users'
  properties: { resource: { id: 'users', partitionKey: { paths: [ '/user_id' ], kind: 'Hash' } } }
}

resource sessionsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = {
  parent: cosmosDb
  name: 'sessions'
  properties: { resource: { id: 'sessions', partitionKey: { paths: [ '/session_id' ], kind: 'Hash' } } }
}

// ── Container Registry ─────────────────────────────────────────────────────
resource acr 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: acrName
  location: location
  sku: { name: 'Basic' }
  properties: { adminUserEnabled: false }
}

// ── Observability ──────────────────────────────────────────────────────────
resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logName
  location: location
  properties: { sku: { name: 'PerGB2018' }, retentionInDays: 30 }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: aiName
  location: location
  kind: 'web'
  properties: { Application_Type: 'web', WorkspaceResourceId: logs.id }
}

// ── Container Apps environment + GM app ────────────────────────────────────
resource cae 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: caeName
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

resource gm 'Microsoft.App/containerApps@2024-03-01' = if (!empty(gmImage)) {
  name: appName
  location: location
  identity: { type: 'SystemAssigned' }   // managed identity → Cosmos data-plane RBAC + Foundry
  properties: {
    managedEnvironmentId: cae.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'http'            // SSE streams over HTTP/1.1; ingress does not buffer
        allowInsecure: false
      }
      registries: [ { server: acr.properties.loginServer, identity: 'system' } ]
    }
    template: {
      containers: [
        {
          name: 'gm'
          image: gmImage
          resources: { cpu: json('1.0'), memory: '2Gi' }
          env: [
            { name: 'RUNTIME', value: 'azure' }
            { name: 'COSMOS_DB_ENDPOINT', value: cosmos.properties.documentEndpoint }
            { name: 'COSMOS_DB_DATABASE', value: 'fantasy-rpg' }
            { name: 'FOUNDRY_PROJECT_ENDPOINT', value: foundryProjectEndpoint }
            { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsights.properties.ConnectionString }
          ]
        }
      ]
      scale: { minReplicas: 1, maxReplicas: 1 }  // single replica: see Dockerfile note on the session lock
    }
  }
}

output cosmosEndpoint string = cosmos.properties.documentEndpoint
output acrLoginServer string = acr.properties.loginServer
output appInsightsConnectionString string = appInsights.properties.ConnectionString
output gmFqdn string = !empty(gmImage) ? gm.properties.configuration.ingress.fqdn : ''
