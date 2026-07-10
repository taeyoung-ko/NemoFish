<template>
  <div class="language-switcher" ref="switcherRef">
    <button class="switcher-trigger" @click="toggleDropdown">
      {{ currentLabel }}
      <span class="caret">{{ open ? '▲' : '▼' }}</span>
    </button>
    <ul v-if="open" class="switcher-dropdown">
      <li
        v-for="loc in availableLocales"
        :key="loc.key"
        class="switcher-option"
        :class="{ active: loc.key === locale }"
        @click="switchLocale(loc.key)"
      >
        {{ loc.label }}
      </li>
    </ul>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { availableLocales } from '@/i18n/index.js'

const { locale } = useI18n()
const open = ref(false)
const switcherRef = ref(null)

const currentLabel = computed(() => {
  const found = availableLocales.find(l => l.key === locale.value)
  return found ? found.label : locale.value
})

const toggleDropdown = () => {
  open.value = !open.value
}

const switchLocale = (key) => {
  locale.value = key
  localStorage.setItem('locale', key)
  document.documentElement.lang = key
  open.value = false
}

const onClickOutside = (e) => {
  if (switcherRef.value && !switcherRef.value.contains(e.target)) {
    open.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', onClickOutside)
  document.documentElement.lang = locale.value
})

onUnmounted(() => {
  document.removeEventListener('click', onClickOutside)
})
</script>

<style scoped>
.language-switcher {
  position: relative;
  display: inline-block;
  font-family: var(--font-sans);
}

/* Light theme (default - for white header backgrounds) */
.switcher-trigger {
  background: var(--surface-1);
  color: var(--ink);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: var(--sp-1) var(--sp-3);
  font-family: var(--font-sans);
  font-size: var(--fs-body);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: border-color var(--motion-base), opacity var(--motion-base);
}

.switcher-trigger:hover {
  border-color: var(--ink-subdued);
}

.caret {
  font-size: var(--fs-label);
  color: var(--ink-subdued);
}

.switcher-dropdown {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 4px;
  background: var(--surface-1);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  list-style: none;
  padding: 4px 0;
  min-width: 100%;
  z-index: 1000;
  box-shadow: var(--shadow-card);
}

.switcher-option {
  padding: 6px 12px;
  font-size: var(--fs-body);
  color: var(--ink);
  cursor: pointer;
  white-space: nowrap;
  transition: background var(--motion-base);
}

.switcher-option:hover {
  background: var(--surface-2);
}

.switcher-option.active {
  color: var(--ink);
  background: var(--primary-tint);
  font-weight: 700;
  border-left: 2px solid var(--primary);
  padding-left: 10px;
}


</style>
