import axiosInstance from './axiosInstance'

export type ProviderModelInfo = {
  providerName: string
  providerType: string
  authType: string
  displayName: string
  description: string
  connectType: string
  defaultModel: string
  models: string[]
}

export type OpenAiModelsResponse = {
  defaultModel: string
  providers: ProviderModelInfo[]
}

export async function getOpenAiModels(): Promise<OpenAiModelsResponse> {
  const { data } = await axiosInstance.get<{
    status: number
    message: string
    data: OpenAiModelsResponse
  }>('/api/v1/ai/providers/models')
  return data.data
}
