import { useQuery } from '@tanstack/react-query'
import { useEffect } from 'react'
import toast from 'react-hot-toast'
import { QUERY_KEY_CHART, fetchChart } from '../api/prices'

export function useChart(metal, range) {
  const query = useQuery({
    queryKey: QUERY_KEY_CHART(metal, range),
    queryFn: () => fetchChart(metal, range),
    staleTime: 60 * 60 * 1000,
    enabled: Boolean(metal && range),
  })

  useEffect(() => {
    if (query.isError) {
      toast.error(`Could not load chart data for ${metal} (${range})`)
    }
  }, [query.isError, metal, range])

  return query
}
