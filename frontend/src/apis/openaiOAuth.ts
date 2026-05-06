import axiosInstance from './axiosInstance'

export type OpenAiOAuthStartRequest = {
  redirectUri?: string | null
  force?: boolean
}

export type OpenAiOAuthStartResponse = {
  status: string
  authorizationUrl: string
  state: string
  redirectUri: string
  scopes: string[]
}

export async function startOpenAiOAuth(
  body: OpenAiOAuthStartRequest = {},
): Promise<OpenAiOAuthStartResponse> {
  const { data } = await axiosInstance.post<{
    status: number
    message: string
    data: OpenAiOAuthStartResponse
  }>('/api/v1/ai/openai/oauth/start', body)
  return data.data
}

export type OpenAiOAuthRefreshResponse = {
  providerName: string
  connected: boolean
  status: string
  scopes: string[]
  expiresAt: string | null
}

export async function refreshOpenAiOAuth(): Promise<OpenAiOAuthRefreshResponse> {
  const { data } = await axiosInstance.post<{
    status: number
    message: string
    data: OpenAiOAuthRefreshResponse
  }>('/api/v1/ai/openai/oauth/refresh', {})
  return data.data
}

export type OpenAiOAuthDisconnectResponse = {
  providerName: string
  connected: boolean
  status: string
  scopes: string[]
  expiresAt: string | null
}

export async function disconnectOpenAiOAuth(): Promise<OpenAiOAuthDisconnectResponse> {
  const { data } = await axiosInstance.delete<{
    status: number
    message: string
    data: OpenAiOAuthDisconnectResponse
  }>('/api/v1/ai/openai/oauth')
  return data.data
}
