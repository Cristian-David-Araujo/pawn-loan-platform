import { computed, ref, watch, type Ref } from 'vue'

/**
 * Checkbox selection over a table's rows, shared by the interest and principal
 * collection tabs — both let the operator tick rows and then pay the ticked total.
 *
 * The pruning watch matters: the interest tab used to keep its selected ids when the
 * operator switched customer, so a hidden id from the previous customer stayed in the
 * set. Interest allocation ignores the selection server-side, which hid the bug, but
 * principal allocation honours it — there it would have moved real money.
 */
export function useRowSelection<T>(rows: Ref<T[]>, keyOf: (row: T) => number) {
  const selected = ref(new Set<number>())

  watch(rows, (next) => {
    const available = new Set(next.map(keyOf))
    const pruned = new Set([...selected.value].filter((id) => available.has(id)))
    if (pruned.size !== selected.value.size) {
      selected.value = pruned
    }
  })

  const isSelected = (id: number) => selected.value.has(id)

  const toggle = (id: number) => {
    // Replace the Set rather than mutate it: Vue does not track Set mutations here.
    const next = new Set(selected.value)
    if (next.has(id)) {
      next.delete(id)
    } else {
      next.add(id)
    }
    selected.value = next
  }

  const allSelected = computed(
    () => rows.value.length > 0 && rows.value.every((row) => selected.value.has(keyOf(row)))
  )

  const toggleAll = () => {
    selected.value = allSelected.value ? new Set() : new Set(rows.value.map(keyOf))
  }

  const selectAll = () => {
    selected.value = new Set(rows.value.map(keyOf))
  }

  const selectedRows = computed(() => rows.value.filter((row) => selected.value.has(keyOf(row))))

  return { selected, selectedRows, isSelected, toggle, toggleAll, selectAll, allSelected }
}
