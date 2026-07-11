<template>
  <Transition name="modal">
    <div v-if="open" class="dd-modal-overlay" @click.self="$emit('close')">
      <div class="dd-modal">
        <div class="dd-modal-header">
          <div class="dd-modal-hinfo">
            <span class="dd-modal-cat">{{ article?.category_name }}</span>
            <span class="dd-modal-title">{{ article?.title || (loading ? '…' : '') }}</span>
            <span class="dd-modal-meta" v-if="article">{{ article.field }} · {{ article.date }}</span>
          </div>
          <button class="dd-close-btn" @click="$emit('close')">×</button>
        </div>
        <div class="dd-modal-body">
          <p v-if="loading" class="dd-modal-loading">…</p>
          <p v-else class="dd-modal-text">{{ article?.body }}</p>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup>
defineProps({ open: Boolean, article: Object, loading: Boolean })
defineEmits(['close'])
</script>

<style scoped>
.dd-modal-overlay {
  position: fixed; inset: 0; background: rgba(0, 0, 0, 0.45);
  display: flex; align-items: center; justify-content: center;
  z-index: 2000; padding: var(--sp-5); font-family: var(--font-sans);
  /* hover 미리보기 — 마우스를 가로채지 않도록(결과 아이템 hover 유지) */
  pointer-events: none;
}
.dd-modal {
  background: var(--surface-1); border-radius: var(--radius-md);
  width: 100%; max-width: 680px; max-height: 85vh; overflow-y: auto;
  box-shadow: var(--shadow-modal); border: 1px solid var(--border);
}
.dd-modal-header {
  display: flex; justify-content: space-between; align-items: flex-start;
  padding: var(--sp-5) var(--sp-5) var(--sp-3); border-bottom: 1px solid var(--border-subtle);
  position: sticky; top: 0; background: var(--surface-1);
  border-radius: var(--radius-md) var(--radius-md) 0 0;
}
.dd-modal-hinfo { display: flex; flex-direction: column; gap: var(--sp-1); min-width: 0; }
.dd-modal-cat { font-size: var(--fs-label); color: var(--ink-muted); font-weight: 600; }
.dd-modal-title { font-size: var(--fs-section); font-weight: 700; color: var(--ink); line-height: 1.4; }
.dd-modal-meta { font-size: var(--fs-label); color: var(--ink-subdued); font-family: var(--font-mono); }
.dd-close-btn {
  border: none; background: none; font-size: 24px; line-height: 1;
  color: var(--ink-subdued); cursor: pointer; padding: 0 var(--sp-1); flex-shrink: 0;
}
.dd-close-btn:hover { color: var(--ink-muted); }
.dd-modal-body { padding: var(--sp-4) var(--sp-5) var(--sp-6); }
.dd-modal-loading { font-size: var(--fs-body); color: var(--ink-subdued); text-align: center; }
.dd-modal-text {
  font-size: var(--fs-body); color: var(--ink-muted); line-height: 1.75;
  margin: 0; white-space: pre-wrap; word-break: break-word;
}
.modal-enter-active, .modal-leave-active { transition: opacity 0.2s; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
</style>
