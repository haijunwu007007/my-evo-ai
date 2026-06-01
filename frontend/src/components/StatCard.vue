<template>
  <div class="stat-card" :style="{ '--accent': color }">
    <div v-if="icon" class="stat-icon">{{ icon }}</div>
    <div class="stat-body">
      <div class="stat-value" :style="{ color }">{{ value }}</div>
      <div class="stat-label">{{ label }}</div>
    </div>
    <div v-if="trend !== undefined" class="stat-trend" :class="trend > 0 ? 'up' : trend < 0 ? 'down' : 'flat'">
      {{ trend > 0 ? '↑' : trend < 0 ? '↓' : '—' }} {{ Math.abs(trend) }}%
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  label: string
  value: string | number
  color?: string
  icon?: string
  trend?: number
}>()
</script>

<style scoped>
.stat-card {
  background: linear-gradient(135deg, var(--bg-card), var(--bg-sidebar));
  border: 1px solid var(--border-subtle);
  border-left: 3px solid var(--accent, #6366f1);
  border-radius: 10px;
  padding: 14px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
}
.stat-icon { font-size: 24px; line-height: 1; }
.stat-body { flex: 1; min-width: 0; }
.stat-value { font-size: 26px; font-weight: 700; line-height: 1.1; }
.stat-label { font-size: 12px; color: var(--text-muted); margin-top: 2px; }
.stat-trend { font-size: 11px; font-weight: 600; padding: 2px 6px; border-radius: 4px; }
.stat-trend.up { color: #10b981; background: rgba(16,185,129,0.12); }
.stat-trend.down { color: #ef4444; background: rgba(239,68,68,0.12); }
.stat-trend.flat { color: #6b7280; background: rgba(107,114,128,0.12); }
</style>
