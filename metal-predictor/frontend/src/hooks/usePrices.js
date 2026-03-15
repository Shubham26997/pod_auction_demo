import { useQuery } from '@tanstack/react-query'
import { useEffect } from 'react'
import toast from 'react-hot-toast'
import { QUERY_KEY_PRICES, fetchPrices } from '../api/prices'
import useStore from '../store/useStore'

export function usePrices() {
  const setPrices = useStore((s) => s.setPrices)

  const query = useQuery({
    queryKey: QUERY_KEY_PRICES,
    queryFn: fetchPrices,
    staleTime: 60 * 60 * 1000,
    refetchInterval: 60 * 60 * 1000,
  })

  useEffect(() => {
    if (query.data) {
      setPrices(query.data)
    }
  }, [query.data, setPrices])

  useEffect(() => {
    if (query.isError) {
      toast.error('Could not load prices — retrying in 1 hour')
    }
  }, [query.isError])

  return query
}
