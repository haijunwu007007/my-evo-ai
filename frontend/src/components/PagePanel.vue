<template>
  <el-card shadow="never" class="evo-panel" :class="accent ? `panel-accent-${accent}` : ''">
    <template v-if="$slots.header || title" #header>
      <div class="panel-header">
        <span class="panel-title">{{ title }}</span>
        <div class="header-actions" v-if="$slots.actions">
          <slot name="actions" />
        </div>
      </div>
    </template>
    <slot />
  </el-card>
</template>

<script setup lang="ts">
defineProps<{
  title?: string
  accent?: 'indigo' | 'green' | 'red' | 'amber'
}>()
</script>

<style scoped>
.evo-panel {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  margin-bottom: 16px;
}
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}
.panel-title { font-size: 14px; }
.header-actions { display: flex; gap: 8px; align-items: center; }
</style>
