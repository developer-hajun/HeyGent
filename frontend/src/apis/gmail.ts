import axiosInstance from './axiosInstance'

interface GmailConnectUrlResponse {
  status: number
  message: string
  data: { url: string }
}

interface GmailStatusResponse {
  status: number
  message: string
  data: { connected: boolean }
}

// Composio Gmail 연결 URL 요청
export const getGmailConnectUrl = async (): Promise<GmailConnectUrlResponse> => {
  const { data } = await axiosInstance.get<GmailConnectUrlResponse>('/api/v1/gmail/connect-url')
  return data
}

// Gmail 연결 상태 조회
export const getGmailStatus = async (): Promise<GmailStatusResponse> => {
  const { data } = await axiosInstance.get<GmailStatusResponse>('/api/v1/gmail/status')
  return data
}

// Gmail 연결 해제
export const disconnectGmail = async () => {
  const { data } = await axiosInstance.delete('/api/v1/gmail/disconnect')
  return data
}
