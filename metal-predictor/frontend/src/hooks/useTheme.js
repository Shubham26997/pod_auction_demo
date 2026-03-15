import { useEffect } from 'react'
import useStore from '../store/useStore'

export function useTheme() {
  const theme = useStore((s) => s.theme)
  const setTheme = useStore((s) => s.setTheme)

  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [theme])

  const toggleTheme = () => setTheme(theme === 'dark' ? 'light' : 'dark')

  return { theme, setTheme, toggleTheme }
}
