<template>
  <div v-if="loading" class="evo-loading">
    <el-skeleton animated :rows="rows" />
  </div>
  <slot v-else />
</template>

<script setup lang="ts">
defineProps<{
  loading: boolean
  rows?: number
}>()
</script>

<style scoped>
.evo-loading { padding: 12px 0; }
</style>
