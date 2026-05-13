import axiosInstance from './axiosInstance'

type ApiResponse<T> = {
  status: number
  message: string
  data: T
}

export type MattermostChannel = {
  id: number
  alias: string
  displayName: string
  defaultChannel: boolean
  webhookConfigured: boolean
  createdAt: string | null
  updatedAt: string | null
}

export type MattermostChannelPayload = {
  alias: string
  displayName: string
  webhookUrl: string
  defaultChannel: boolean
}

type MattermostWebhookResponse = {
  sent: boolean
}

export type MattermostMessageResponse = {
  sent: boolean
  target: string
  displayName: string
}

export async function getMattermostChannels() {
  const { data } = await axiosInstance.get<ApiResponse<MattermostChannel[]>>(
    '/api/v1/mattermost/channels',
  )
  return data.data
}

export async function createMattermostChannel(payload: MattermostChannelPayload) {
  const { data } = await axiosInstance.post<ApiResponse<MattermostChannel>>(
    '/api/v1/mattermost/channels',
    payload,
  )
  return data.data
}

export async function updateMattermostChannel(
  channelId: number,
  payload: MattermostChannelPayload,
) {
  const { data } = await axiosInstance.put<ApiResponse<MattermostChannel>>(
    `/api/v1/mattermost/channels/${channelId}`,
    payload,
  )
  return data.data
}

export async function deleteMattermostChannel(channelId: number) {
  await axiosInstance.delete(`/api/v1/mattermost/channels/${channelId}`)
}

export async function setDefaultMattermostChannel(channelId: number) {
  const { data } = await axiosInstance.post<ApiResponse<MattermostChannel>>(
    `/api/v1/mattermost/channels/${channelId}/default`,
  )
  return data.data
}

export async function sendMattermostMessage(payload: { target?: string; message: string }) {
  const { data } = await axiosInstance.post<ApiResponse<MattermostMessageResponse>>(
    '/api/v1/mattermost/messages',
    payload,
  )
  return data.data
}

export async function sendMattermostWebhook(payload: { webhookUrl: string; message: string }) {
  const { data } = await axiosInstance.post<ApiResponse<MattermostWebhookResponse>>(
    '/api/v1/mattermost/webhook',
    payload,
  )
  return data.data
}
