import axiosInstance from './axiosInstance'

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
  body: SaveOpenAiApiKeyRequest,
): Promise<SaveOpenAiApiKeyResponse> {
  const { data } = await axiosInstance.post<{
    status: number
    message: string
    data: SaveOpenAiApiKeyResponse
  }>('/api/v1/ai/openai/api-key', body)
  return data.data
}

export type DeleteOpenAiApiKeyResponse = {
  providerName: string
  connected: boolean
  status: string
  updatedAt: string | null
}

export async function deleteOpenAiApiKey(): Promise<DeleteOpenAiApiKeyResponse> {
  const { data } = await axiosInstance.delete<{
    status: number
    message: string
    data: DeleteOpenAiApiKeyResponse
  }>('/api/v1/ai/openai/api-key')
  return data.data
}
