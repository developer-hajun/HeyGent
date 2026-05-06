import axiosInstance from './axiosInstance'

export type OpenAiProviderStatus =
  | 'connected'
  | 'not_connected'
  | 'expired'
  | 'available'
  | 'disabled'

export type OpenAiProvider = {
  providerName: string
  authType: 'api_key' | 'oauth'
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
  }>('/api/v1/ai/openai/providers')
  return data.data
}
