import { ref, computed, watch, type Ref } from 'vue'

export function usePagination<T>(sourceArray: Ref<T[]>, itemsPerPage: number = 10) {
  const currentPage = ref(1)

  // Reset to page 1 if the source array changes significantly (e.g. filtered)
  watch(sourceArray, (newArr, oldArr) => {
    if (newArr.length !== oldArr?.length) {
      currentPage.value = 1
    }
  })

  const paginatedArray = computed(() => {
    const start = (currentPage.value - 1) * itemsPerPage
    return sourceArray.value.slice(start, start + itemsPerPage)
  })

  return {
    currentPage,
    paginatedArray
  }
}
