import axiosInstance from './axiosInstance'

export type GetOpenAiUsageRequest = {
  providerName: string
  from?: string
  to?: string
}

export type OpenAiUsageResponse = {
  providerName: string
  usage: Record<string, unknown>
  costs: Record<string, unknown>
}

export async function getOpenAiUsage(params: GetOpenAiUsageRequest): Promise<OpenAiUsageResponse> {
  const { data } = await axiosInstance.get<{
    status: number
    message: string
    data: OpenAiUsageResponse
  }>('/api/v1/ai/openai/usages/me', { params })
  return data.data
}
