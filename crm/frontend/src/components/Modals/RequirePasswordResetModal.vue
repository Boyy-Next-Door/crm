<template>
  <!--
    Non-dismissable password-set modal, shown to users whose accounts were
    just created via the CRM invitation flow (window.require_password_reset).
    :dismissable="false" removes the close button + prevents ESC/backdrop close;
    the only exit is a successful password submission.
  -->
  <Dialog
    v-model:open="open"
    :title="__('Please set your password')"
    :dismissable="false"
    :options="{ size: 'sm' }"
  >
    <template #default>
      <div class="flex flex-col gap-4">
        <p class="text-p-base text-ink-gray-6 leading-5">
          {{
            __(
              'Welcome to the CRM! Since you joined via an invitation, please set a password for your account before continuing.',
            )
          }}
        </p>
        <div>
          <Password
            v-model="newPassword"
            :placeholder="__('New Password')"
            maxLength="50"
            autocomplete="new-password"
          >
            <template #prefix>
              <LockKeyhole class="size-4 text-ink-gray-4" />
            </template>
          </Password>
        </div>
        <div>
          <Password
            v-model="confirmPassword"
            :placeholder="__('Confirm Password')"
            maxLength="50"
            autocomplete="new-password"
          >
            <template #prefix>
              <LockKeyhole class="size-4 text-ink-gray-4" />
            </template>
          </Password>
        </div>
      </div>
    </template>
    <template #actions>
      <div class="flex flex-col gap-2">
        <p
          v-if="hint"
          class="text-sm"
          :class="hintOk ? 'text-ink-green-6' : 'text-ink-red-6'"
        >
          {{ hint }}
        </p>
        <Button
          variant="solid"
          class="w-full"
          :label="__('Set Password')"
          :disabled="!canSubmit"
          :loading="setPassword.loading"
          @click="setPassword.submit()"
        />
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import LockKeyhole from '~icons/lucide/lock-keyhole'
import { Dialog, Button, Password, toast, createResource } from 'frappe-ui'
import { computed, ref, watch } from 'vue'

// The parent controls visibility via v-model; but once we open, we don't
// let the user close it — see :dismissable="false" above.
const open = defineModel({ type: Boolean, default: false })

const newPassword = ref('')
const confirmPassword = ref('')
const hint = ref('')
const hintOk = ref(false)

// Same policy the ChangePasswordModal enforces client-side. Backend applies
// Frappe's own strength policy on top, which may reject even more.
function isStrongPassword(password) {
  const regex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z\d\s]).{8,}$/
  return regex.test(password)
}

watch([newPassword, confirmPassword], () => {
  hint.value = ''
  hintOk.value = false
  if (newPassword.value && newPassword.value.length < 8) {
    hint.value = __('Password must be at least 8 characters')
    return
  }
  if (newPassword.value && !isStrongPassword(newPassword.value)) {
    hint.value = __('Password must contain lowercase, uppercase, number, and symbol')
    return
  }
  if (
    confirmPassword.value.length &&
    newPassword.value !== confirmPassword.value
  ) {
    hint.value = __('Passwords do not match')
    return
  }
  if (
    newPassword.value &&
    confirmPassword.value &&
    newPassword.value === confirmPassword.value
  ) {
    hint.value = __('Passwords match')
    hintOk.value = true
  }
})

const canSubmit = computed(
  () =>
    newPassword.value &&
    confirmPassword.value &&
    newPassword.value === confirmPassword.value &&
    isStrongPassword(newPassword.value) &&
    !setPassword.loading,
)

const setPassword = createResource({
  url: 'crm.api.auth.set_own_password',
  makeParams() {
    return { new_password: newPassword.value }
  },
  onSuccess() {
    toast.success(__('Password set successfully'))
    // Reload so the fresh boot payload comes back without the flag, and any
    // downstream code that reads window.require_password_reset sees false.
    window.location.reload()
  },
  onError(err) {
    // Frappe's password validation errors surface here — show verbatim.
    toast.error(err?.messages?.[0] || __('Failed to set password'))
  },
})
</script>
