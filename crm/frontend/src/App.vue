<template>
  <FrappeUIProvider>
    <NotPermitted v-if="$route.name === 'Not Permitted'" />
    <router-view v-else-if="$route.name === 'Onboarding'" />
    <Layout v-else-if="session.isLoggedIn" class="isolate">
      <router-view :key="$route.fullPath" />
    </Layout>
    <Dialogs />
    <DoctypeModals />
    <EventNotificationPopup />
    <!--
      Non-dismissable "please set your password" modal for users that just
      joined via a CRM invitation. Boot payload carries the flag on
      window.require_password_reset; the modal reloads the page after a
      successful set, so the flag is naturally cleared on next boot.
    -->
    <RequirePasswordResetModal
      v-if="session.isLoggedIn && needsPasswordReset"
      v-model="needsPasswordReset"
    />
  </FrappeUIProvider>
</template>

<script setup>
import NotPermitted from '@/pages/NotPermitted.vue'
import EventNotificationPopup from '@/components/EventNotificationPopup.vue'
import DoctypeModals from '@/components/Modals/DoctypeModals.vue'
import RequirePasswordResetModal from '@/components/Modals/RequirePasswordResetModal.vue'
import { Dialogs } from '@/utils/dialogs'
import { sessionStore } from '@/stores/session'
import { FrappeUIProvider, setConfig, useTheme } from 'frappe-ui'
import { computed, defineAsyncComponent, provide, ref } from 'vue'

const session = sessionStore()
provide('session', session)

const { setTheme } = useTheme()
if (!localStorage.getItem('theme')) {
  setTheme('light')
}

const MobileLayout = defineAsyncComponent(
  () => import('./components/Layouts/MobileLayout.vue'),
)
const DesktopLayout = defineAsyncComponent(
  () => import('./components/Layouts/DesktopLayout.vue'),
)
const Layout = computed(() => {
  if (window.innerWidth < 640) {
    return MobileLayout
  } else {
    return DesktopLayout
  }
})

setConfig('systemTimezone', window.timezone?.system || null)
setConfig('localTimezone', window.timezone?.user || null)
setConfig('translatedMessages', window.translated_messages || {})

// Read the flag from the boot payload (see crm/www/crm.py:get_boot).
// It's baked into window at page-render time by Frappe, so no async fetch
// is needed — the modal decision is made synchronously on first render.
const needsPasswordReset = ref(!!window.require_password_reset)
</script>
