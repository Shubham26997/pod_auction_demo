import { create } from 'zustand'
import { persist } from 'zustand/middleware'

const useStore = create(
  persist(
    (set) => ({
      theme: 'dark',
      chartModal: { isOpen: false, metal: null },
      chatDrawer: { isOpen: false, metal: null },
      prices: {},

      setTheme: (theme) => {
        set({ theme })
        if (theme === 'dark') {
          document.documentElement.classList.add('dark')
        } else {
          document.documentElement.classList.remove('dark')
        }
      },

      openChartModal: (metal) => set({ chartModal: { isOpen: true, metal } }),
      closeChartModal: () => set({ chartModal: { isOpen: false, metal: null } }),

      openChatDrawer: (metal) => set({ chatDrawer: { isOpen: true, metal } }),
      closeChatDrawer: () => set({ chatDrawer: { isOpen: false, metal: null } }),

      setPrices: (prices) => set({ prices }),
    }),
    {
      name: 'metalsense-store',
      partialize: (state) => ({ theme: state.theme }),
    }
  )
)

export default useStore
