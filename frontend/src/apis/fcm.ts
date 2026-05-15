import aiAxiosInstance from './aiAxiosInstance'

export const registerFcmToken = async (token: string): Promise<void> => {
  await aiAxiosInstance.post('/fcm/token', { token })
}
