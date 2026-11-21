@description('Azure region for all resources')
param location string = resourceGroup().location

@description('Existing Container Apps managed environment ID')
param containerAppsEnvironmentId string

@description('Container image (e.g., myacr.azurecr.io/cloud-watchdog:latest)')
param containerImage string

@description('Cron expression for the scheduled audit (UTC, default: daily at 07:00 UTC)')
param cronExpression string = '0 7 * * *'

@description('Target Azure resource group to audit (leave empty to audit the entire subscription)')
param targetResourceGroup string = ''

@description('Azure OpenAI endpoint URL')
param azureOpenAiEndpoint string

@description('Azure OpenAI deployment name')
param azureOpenAiDeployment string = 'gpt-4.1-mini'

@description('Optional Azure Key Vault name storing the OpenAI API key (leave empty to use Managed Identity token auth)')
param keyVaultName string = ''

@description('Key Vault secret name for the Azure OpenAI API key')
param keyVaultSecretName string = 'azure-openai-api-key'

resource watchdogJob 'Microsoft.App/jobs@2024-03-01' = {
  name: 'cloud-cost-watchdog-job'
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    environmentId: containerAppsEnvironmentId
    configuration: {
      triggerType: 'Schedule'
      replicaTimeout: 300
      replicaRetryLimit: 1
      scheduleTriggerConfig: {
        cronExpression: cronExpression
        parallelism: 1
        replicaCompletionCount: 1
      }
    }
    template: {
      containers: [
        {
          name: 'watchdog'
          image: containerImage
          args: empty(targetResourceGroup) ? ['--subscription'] : [targetResourceGroup]
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          env: [
            {
              name: 'AZURE_OPENAI_ENDPOINT'
              value: azureOpenAiEndpoint
            }
            {
              name: 'AZURE_OPENAI_DEPLOYMENT'
              value: azureOpenAiDeployment
            }
            {
              name: 'AZURE_USE_MANAGED_IDENTITY'
              value: 'true'
            }
            {
              name: 'AZURE_KEY_VAULT_NAME'
              value: keyVaultName
            }
            {
              name: 'AZURE_KEY_VAULT_SECRET_NAME'
              value: keyVaultSecretName
            }
          ]
        }
      ]
    }
  }
}

@description('Principal ID of the job Managed Identity — grant Reader, Cost Management Reader, and Cognitive Services OpenAI User (or Key Vault Secrets User)')
output principalId string = watchdogJob.identity.principalId
