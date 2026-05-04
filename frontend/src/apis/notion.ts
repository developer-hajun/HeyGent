import axiosInstance from './axiosInstance'

interface NotionConnectUrlResponse {
  status: number
  message: string
  data: { url: string }
}

interface NotionStatusResponse {
  status: number
  message: string
  data: { connected: boolean }
}

// Composio Notion 연결 URL 요청
export const getNotionConnectUrl = async (): Promise<NotionConnectUrlResponse> => {
  const { data } = await axiosInstance.get<NotionConnectUrlResponse>('/api/v1/notion/connect-url')
  return data
}

// Notion 연결 상태 조회
export const getNotionStatus = async (): Promise<NotionStatusResponse> => {
  const { data } = await axiosInstance.get<NotionStatusResponse>('/api/v1/notion/status')
  return data
}

// Notion 연결 해제
export const disconnectNotion = async () => {
  const { data } = await axiosInstance.delete('/api/v1/notion/disconnect')
  return data
}
