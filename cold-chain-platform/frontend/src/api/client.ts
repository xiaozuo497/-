import axios from 'axios'

export const apiClient = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('cold-chain-access-token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && window.location.pathname !== '/login') {
      localStorage.removeItem('cold-chain-current-user')
      localStorage.removeItem('cold-chain-access-token')
      localStorage.removeItem('cold-chain-last-solution')
      localStorage.removeItem('cold-chain-all-solutions')
      window.location.assign('/login')
    }
    return Promise.reject(error)
  },
)
