<template>
  <div id="content">
    <div class="well" id="general_presentation">
      <div id="form_container" :class="formClass">
        <RouterView />
      </div>
      <div id="demo-scene" class="css-gradient-bg">
        <div class="demo-scene-placeholder">
          <i class="fa fa-cube"></i>
          <p>{{ t('LOGIN_3D_PLACEHOLDER') }}</p>
        </div>
      </div>
    </div>

    <div id="detail_presentation" v-if="!isMenuPage">
      <div class="well">
        <h2>{{ t('MANAGE_DOCUMENTS') }}</h2>
        <ul>
          <li v-for="(s, i) in t('MANAGE_DOCUMENTS_STRINGS', { default: [] })" :key="i">{{ s }}</li>
        </ul>
      </div>
      <div class="well">
        <h2>{{ t('MANAGE_PRODUCTS') }}</h2>
        <ul>
          <li v-for="(s, i) in t('MANAGE_PRODUCTS_STRINGS', { default: [] })" :key="i">{{ s }}</li>
        </ul>
      </div>
      <div class="well">
        <h2>{{ t('TRACK_CHANGES') }}</h2>
        <ul>
          <li v-for="(s, i) in t('TRACK_CHANGES_STRINGS', { default: [] })" :key="i">{{ s }}</li>
        </ul>
      </div>
      <div class="well">
        <h2>{{ t('SOCIAL_FEATURES') }}</h2>
        <ul>
          <li v-for="(s, i) in t('SOCIAL_FEATURES_STRINGS', { default: [] })" :key="i">{{ s }}</li>
        </ul>
      </div>
    </div>

    <div id="footer">
      <p>Copyright 2006-2026 - <a href="http://www.docdokuplm.com">DocDokuPLM</a> — Vue 3 版</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, RouterView } from 'vue-router'
import { useI18n } from 'vue-i18n'

const { t, tm } = useI18n()
const route = useRoute()

const isMenuPage = computed(() => route.name === 'menu')
const isAccountCreation = computed(() => route.name === 'create-account')

const formClass = computed(() => isAccountCreation.value ? 'put-above' : 'put-right')
</script>

<style scoped>
.css-gradient-bg {
  background: linear-gradient(135deg, #4a90e2 0%, #7b68ee 50%, #50c9c3 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 14px;
  position: relative;
  overflow: hidden;
}
.css-gradient-bg::before {
  content: '';
  position: absolute;
  top: -50%; left: -50%;
  width: 200%; height: 200%;
  background: radial-gradient(circle, rgba(255,255,255,0.1) 1px, transparent 1px);
  background-size: 40px 40px;
  animation: scene-drift 60s linear infinite;
}
@keyframes scene-drift {
  from { transform: translate(0, 0); }
  to   { transform: translate(40px, 40px); }
}
.demo-scene-placeholder {
  text-align: center;
  z-index: 1;
}
.demo-scene-placeholder i {
  font-size: 80px;
  display: block;
  margin-bottom: 12px;
  opacity: 0.8;
}
</style>
