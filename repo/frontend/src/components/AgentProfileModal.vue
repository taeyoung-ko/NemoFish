<template>
  <Transition name="modal">
    <div v-if="profile" class="profile-modal-overlay" @click.self="$emit('close')">
      <div class="profile-modal">
        <div class="modal-header">
          <div class="modal-header-info">
            <div class="modal-name-row">
              <span class="modal-realname">{{ profile.name }}</span>
              <span class="modal-username">@{{ profile.username }}</span>
            </div>
            <span class="modal-profession">{{ profile.profession }}</span>
          </div>
          <button class="close-btn" @click="$emit('close')">×</button>
        </div>

        <div class="modal-body">
          <div class="modal-info-grid">
            <div class="info-item">
              <span class="info-label">{{ $t('step2.profileModalAge') }}</span>
              <span class="info-value">{{ profile.age || '-' }} {{ $t('step2.yearsOld') }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">{{ $t('step2.profileModalGender') }}</span>
              <span class="info-value">{{ { male: $t('step2.genderMale'), female: $t('step2.genderFemale'), other: $t('step2.genderOther') }[profile.gender] || profile.gender }}</span>
            </div>
            <div class="info-item" v-if="profile.profession">
              <span class="info-label">{{ $t('step2.profileModalProfession') }}</span>
              <span class="info-value">{{ profile.profession }}</span>
            </div>
            <div class="info-item" v-if="profile.province || profile.district">
              <span class="info-label">{{ $t('step2.profileModalRegion') }}</span>
              <span class="info-value">{{ (profile.district || profile.province || '').replace('-', ' ') }}</span>
            </div>
            <div class="info-item" v-if="profile.education_level">
              <span class="info-label">{{ $t('step2.profileModalEducation') }}</span>
              <span class="info-value">{{ profile.education_level }}{{ profile.bachelors_field && profile.bachelors_field !== '해당없음' ? ' · ' + profile.bachelors_field : '' }}</span>
            </div>
            <div class="info-item" v-if="profile.marital_status">
              <span class="info-label">{{ $t('step2.profileModalMarital') }}</span>
              <span class="info-value">{{ profile.marital_status }}</span>
            </div>
            <div class="info-item" v-if="profile.family_type">
              <span class="info-label">{{ $t('step2.profileModalFamily') }}</span>
              <span class="info-value">{{ profile.family_type }}</span>
            </div>
            <div class="info-item" v-if="profile.housing_type">
              <span class="info-label">{{ $t('step2.profileModalHousing') }}</span>
              <span class="info-value">{{ profile.housing_type }}</span>
            </div>
            <div class="info-item" v-if="profile.military_status && profile.military_status !== '해당없음'">
              <span class="info-label">{{ $t('step2.profileModalMilitary') }}</span>
              <span class="info-value">{{ profile.military_status }}</span>
            </div>
            <div class="info-item" v-if="profile.country">
              <span class="info-label">{{ $t('step2.profileModalCountry') }}</span>
              <span class="info-value">{{ profile.country }}</span>
            </div>
          </div>

          <div class="modal-section">
            <span class="section-label">{{ $t('step2.profileModalBio') }}</span>
            <p class="section-bio">{{ profile.bio || $t('step2.noBio') }}</p>
          </div>

          <div class="modal-section" v-if="profile.skills?.length">
            <span class="section-label">{{ $t('step2.profileModalSkills') }}</span>
            <div class="topics-grid">
              <span v-for="s in profile.skills" :key="s" class="topic-item skill-item">{{ s }}</span>
            </div>
          </div>

          <div class="modal-section" v-if="profile.interested_topics?.length">
            <span class="section-label">{{ $t('step2.profileModalTopics') }}</span>
            <div class="topics-grid">
              <span v-for="topic in profile.interested_topics" :key="topic" class="topic-item">{{ topic }}</span>
            </div>
          </div>

          <div class="modal-section" v-if="profile.persona">
            <span class="section-label">{{ $t('step2.profileModalPersona') }}</span>
            <div class="persona-content">
              <p class="section-persona">{{ profile.persona }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup>
defineProps({ profile: Object })
defineEmits(['close'])
</script>

<style scoped>
.profile-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 20px;
  font-family: var(--font-sans);
}
.profile-modal {
  background: var(--surface-1);
  border-radius: var(--radius-md);
  width: 100%;
  max-width: 560px;
  max-height: 85vh;
  overflow-y: auto;
  box-shadow: var(--shadow-modal);
  border: 1px solid var(--border);
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 20px 22px 14px;
  border-bottom: 1px solid var(--border-subtle);
  position: sticky;
  top: 0;
  background: var(--surface-1);
  border-radius: var(--radius-md) var(--radius-md) 0 0;
}
.modal-name-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.modal-realname { font-size: var(--fs-section); font-weight: 700; color: var(--ink); }
.modal-username { font-size: var(--fs-label); color: var(--ink-subdued); font-family: var(--font-mono); }
.modal-profession { display: block; margin-top: 4px; font-size: var(--fs-body); color: var(--ink-muted); }
.close-btn {
  border: none; background: none; font-size: 24px; line-height: 1;
  color: var(--ink-subdued); cursor: pointer; padding: 0 4px;
}
.close-btn:hover { color: var(--ink-muted); }
.modal-body { padding: 16px 22px 24px; }
.modal-info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px 16px;
  margin-bottom: 18px;
}
.info-item { display: flex; flex-direction: column; gap: 2px; }
.info-label { font-size: var(--fs-label); color: var(--ink-subdued); }
.info-value { font-size: var(--fs-body); color: var(--ink); font-weight: 500; }
.modal-section { margin-top: 16px; }
.section-label {
  display: block; font-size: var(--fs-label); font-weight: 700; color: var(--ink-muted);
  margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.4px;
}
.section-bio { font-size: var(--fs-body); color: var(--ink-muted); line-height: 1.6; margin: 0; }
.topics-grid { display: flex; flex-wrap: wrap; gap: 6px; }
.topic-item {
  font-size: var(--fs-label); color: var(--link); background: var(--status-provisioning-bg);
  padding: 4px 10px; border-radius: var(--radius-pill);
}
.topic-item.skill-item { color: var(--status-running); background: var(--status-running-bg); }
.persona-content {
  background: var(--surface-2); border-radius: var(--radius-md); padding: 12px 14px;
  border: 1px solid var(--border-subtle);
}
.section-persona {
  font-size: var(--fs-body); color: var(--ink-muted); line-height: 1.7; margin: 0; white-space: pre-wrap;
}
.modal-enter-active, .modal-leave-active { transition: opacity 0.2s; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
</style>
