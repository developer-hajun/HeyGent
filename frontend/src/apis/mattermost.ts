import axiosInstance from './axiosInstance'

type ApiResponse<T> = {
  status: number
  message: string
  data: T
}

type MattermostWebhookResponse = {
  sent: boolean
}

export async function sendMattermostWebhook(payload: { webhookUrl: string; message: string }) {
  const { data } = await axiosInstance.post<ApiResponse<MattermostWebhookResponse>>(
    '/api/v1/mattermost/webhook',
    payload,
  )
  return data.data
}
