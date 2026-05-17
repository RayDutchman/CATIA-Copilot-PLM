<template>
  <div class="notifications">
    <div v-if="error" class="alert alert-error">
      <button type="button" class="close" @click="error = ''">×</button>
      {{ error }}
    </div>
  </div>

  <div class="margin">
    <h3>{{ t('ORGANIZATION_ADMINISTRATION') }}</h3>

    <!-- 未创建组织 -->
    <template v-if="!hasOrg">
      <p>
        <i class="fa fa-exclamation-triangle"></i>
        <em>{{ t('NO_ORGANIZATION_EXISTS') }}</em>
      </p>
      <router-link to="/create">{{ t('CREATE_ORGANIZATION_SUBTITLE') }}</router-link>
    </template>

    <!-- 已有组织 -->
    <template v-else>
      <div class="home-organization-list-container">
        <div class="well-large well home-organization">
          <div>
            <h4>
              <i class="fa fa-graduation-cap"></i>
              {{ org.name }}
              <br />
              <small>{{ org.description }}</small>
            </h4>
          </div>

          <ul class="unstyled">
            <li>
              <router-link to="/members">{{ t('MEMBERS') }}</router-link>
              (<span>{{ membersCount }}</span>)
            </li>
          </ul>

          <div class="organization-actions">
            <router-link v-if="isOwner" to="/edit">{{ t('EDIT') }}</router-link>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../../vue-common/store/auth.js'
import { useOrgStore }  from '../store/org.js'

const { t }     = useI18n()
const authStore = useAuthStore()
const orgStore  = useOrgStore()

const error        = ref('')
const membersCount = ref(0)

const hasOrg  = computed(() => orgStore.hasOrg)
const org     = computed(() => orgStore.organization || {})
const isOwner = computed(() =>
  !!orgStore.organization && authStore.login === orgStore.organization.owner
)

onMounted(async () => {
  if (hasOrg.value) {
    try {
      const members = await orgStore.fetchMembers()
      membersCount.value = members.length
    } catch (e) {
      error.value = e.message
    }
  }
})
</script>
