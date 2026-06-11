import axiosInstance from './axiosInstance'

export type OpenAiProviderStatus =
  | 'connected'
  | 'not_connected'
  | 'expired'
  | 'available'
  | 'disabled'

export type OpenAiProvider = {
  providerName: string
  providerType: string
  authType: 'api_key' | 'oauth'
  displayName: string
  description: string
  connectType: string
  defaultModel: string
  models: string[]
  connected: boolean
  available: boolean
  expiresAt: string | null
  status: OpenAiProviderStatus
}

export type OpenAiProvidersResponse = {
  providers: OpenAiProvider[]
}

export async function getOpenAiProviders(): Promise<OpenAiProvidersResponse> {
  const { data } = await axiosInstance.get<{
    status: number
    message: string
    data: OpenAiProvidersResponse
  }>('/api/v1/ai/providers')
  return data.data
}
