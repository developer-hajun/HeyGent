import axiosInstance from './axiosInstance'

export type OpenAiModelsResponse = {
  defaultModel: string
  models: string[]
}

export async function getOpenAiModels(): Promise<OpenAiModelsResponse> {
  const { data } = await axiosInstance.get<{
    status: number
    message: string
    data: OpenAiModelsResponse
  }>('/api/v1/ai/openai/models')
  return data.data
}
