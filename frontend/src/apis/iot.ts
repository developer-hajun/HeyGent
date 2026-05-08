import axiosInstance from './axiosInstance'

export interface IotDevice {
  id: number
  deviceId: string
  displayName: string | null
  status: 'ACTIVE' | 'INACTIVE'
  lastSeenAt: string | null
  createdAt: string | null
  updatedAt: string | null
}

export interface GetIotDevicesResponse {
  status: number
  message: string
  data: IotDevice[]
}

export const getIotDevices = async (): Promise<GetIotDevicesResponse> => {
  const { data } = await axiosInstance.get<GetIotDevicesResponse>('/api/v1/iot/devices')
  return data
}

export interface DeleteIotDeviceResponse {
  status: number
  message: string
}

export const deleteIotDevice = async (deviceId: string): Promise<DeleteIotDeviceResponse> => {
  const { data } = await axiosInstance.delete<DeleteIotDeviceResponse>(
    `/api/v1/iot/devices/${deviceId}`,
  )
  return data
}

export interface PairIotDeviceRequest {
  pairCode: string
  displayName?: string
}

export interface PairIotDeviceResponse {
  status: number
  message: string
  data: IotDevice
}

export const pairIotDevice = async (body: PairIotDeviceRequest): Promise<PairIotDeviceResponse> => {
  const { data } = await axiosInstance.post<PairIotDeviceResponse>('/api/v1/iot/devices/pair', body)
  return data
}
