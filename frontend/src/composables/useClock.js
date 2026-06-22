import { ref, onMounted, onUnmounted, computed } from 'vue'

export function useClock() {
  const currentTime = ref(new Date())
  let timer = null

  onMounted(() => {
    timer = setInterval(() => {
      currentTime.value = new Date()
    }, 1000)
  })

  onUnmounted(() => {
    if (timer) clearInterval(timer)
  })

  const formattedTime = computed(() => {
    return currentTime.value.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  })

  const formattedDate = computed(() => {
    return currentTime.value.toLocaleDateString([], { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })
  })

  return {
    currentTime,
    formattedTime,
    formattedDate
  }
}
