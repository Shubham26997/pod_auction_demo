import api from './axios'

export const QUERY_KEY_PRICES = ['prices']
export const QUERY_KEY_CHART = (metal, range) => ['chart', metal, range]

export const fetchPrices = async () => {
  const { data } = await api.get('/api/prices')
  return data
}

export const fetchChart = async (metal, range) => {
  const { data } = await api.get(`/api/chart/${metal}`, { params: { range } })
  return data
}
