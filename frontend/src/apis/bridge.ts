import axiosInstance from './axiosInstance'

export interface BridgeDevice {
  id: number
  deviceName: string
  createdAt: string | null
  lastSeenAt: string | null
  revokedAt: string | null
  online: boolean
}

export interface BridgePairingCode {
  code: string
  expiresAt: string
}

export interface ApiEnvelope<T> {
  status: number
  message: string
  data: T
}

export const issueBridgePairingCode = async (): Promise<BridgePairingCode> => {
  const { data } =
    await axiosInstance.post<ApiEnvelope<BridgePairingCode>>('/api/v1/bridge/pairing')
  return data.data
}

export const listBridgeDevices = async (): Promise<BridgeDevice[]> => {
  const { data } = await axiosInstance.get<ApiEnvelope<BridgeDevice[]>>('/api/v1/bridge/devices')
  return data.data
}

export const revokeBridgeDevice = async (deviceId: number): Promise<void> => {
  await axiosInstance.delete(`/api/v1/bridge/devices/${deviceId}`)
}
