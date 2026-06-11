import axiosInstance from './axiosInstance'

export type ProviderName = 'openai_api_key' | 'gemini_api_key' | 'claude_api_key'

export type SaveOpenAiApiKeyRequest = {
  apiKey: string
}

export type SaveOpenAiApiKeyResponse = {
  providerName: string
  connected: boolean
  status: string
  updatedAt: string | null
}

export async function saveOpenAiApiKey(
  providerName: ProviderName,
  body: SaveOpenAiApiKeyRequest,
): Promise<SaveOpenAiApiKeyResponse> {
  const { data } = await axiosInstance.post<{
    status: number
    message: string
    data: SaveOpenAiApiKeyResponse
  }>(`/api/v1/ai/providers/${providerName}/api-key`, body)
  return data.data
}

export type DeleteOpenAiApiKeyResponse = {
  providerName: string
  connected: boolean
  status: string
  updatedAt: string | null
}

export async function deleteOpenAiApiKey(
  providerName: ProviderName,
): Promise<DeleteOpenAiApiKeyResponse> {
  const { data } = await axiosInstance.delete<{
    status: number
    message: string
    data: DeleteOpenAiApiKeyResponse
  }>(`/api/v1/ai/providers/${providerName}/api-key`)
  return data.data
}
