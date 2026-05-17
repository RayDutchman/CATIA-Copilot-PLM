<template>
  <div :class="['alert', alertClass, 'alert-dismissible']" role="alert">
    <button type="button" class="close" @click="$emit('dismiss')" aria-label="Close">
      <span aria-hidden="true">&times;</span>
    </button>
    <strong v-if="title">{{ title }} </strong>
    <span>{{ message }}</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  type:    { type: String, default: 'info' },   // success | error | info | warning
  title:   { type: String, default: '' },
  message: { type: String, required: true },
})

defineEmits(['dismiss'])

const alertClass = computed(() => {
  const map = { success: 'alert-success', error: 'alert-error', info: 'alert-info', warning: 'alert-warning' }
  return map[props.type] || 'alert-info'
})
</script>
