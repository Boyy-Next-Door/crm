<template>
  <div class="flex flex-col h-full">
    <!--
      Template download strip — shown above the standard Frappe DataImport
      widget. Managers can grab a ready-to-import CSV (English headers,
      because Frappe's importer matches column names to fieldnames) plus
      an all-in-one zip with a Chinese cheatsheet.
    -->
    <div
      class="flex flex-wrap items-center gap-2 px-6 py-3 border-b bg-surface-gray-1"
    >
      <span class="text-sm text-ink-gray-6 mr-2">
        {{ __('Download Import Templates:') }}
      </span>

      <Button
        variant="subtle"
        theme="gray"
        size="sm"
        :label="__('All Templates (zip + guide)')"
        @click="downloadAllTemplatesZip"
      >
        <template #prefix>
          <PackageIcon class="w-4 h-4" />
        </template>
      </Button>

      <span class="mx-1 text-ink-gray-4">|</span>

      <Button
        v-for="dt in singleDoctypes"
        :key="dt.name"
        variant="ghost"
        size="sm"
        :label="__(dt.label)"
        @click="downloadTemplate(dt.name)"
      >
        <template #prefix>
          <DownloadIcon class="w-4 h-4" />
        </template>
      </Button>
    </div>

    <!-- The stock Frappe importer widget — untouched. -->
    <div class="flex-1 overflow-auto">
      <DataImport
        :doctype="route.params.doctype"
        :importName="route.params.importName"
        :doctypeMap="doctypeMap"
      />
    </div>
  </div>
</template>

<script setup>
import { Button, usePageMeta, toast } from 'frappe-ui'
import { DataImport } from 'frappe-ui/frappe'
import { useRoute } from 'vue-router'
import DownloadIcon from '~icons/lucide/download'
import PackageIcon from '~icons/lucide/package'

const route = useRoute()

const doctypeMap = {
  'CRM Lead': {
    title: 'Leads',
    listRoute: '/crm/leads',
    pageRoute: `/crm/leads/docname`,
  },
  'CRM Deal': {
    title: 'Deals',
    listRoute: '/crm/deals',
    pageRoute: `/crm/deals/docname`,
  },
  Contact: {
    title: 'Contacts',
    listRoute: '/crm/contacts',
    pageRoute: `/crm/contacts/docname`,
  },
  'CRM Task': {
    title: 'Tasks',
    listRoute: '/crm/tasks',
  },
  'CRM Organization': {
    title: 'Organizations',
    listRoute: '/crm/organizations',
    pageRoute: `/crm/organizations/docname`,
  },
  'CRM Call Log': {
    title: 'Call Log',
    listRoute: '/crm/call-logs',
  },
}

// Only the four business doctypes we ship a curated template for.
// Order chosen to match the recommended import order: create parents
// (organizations) before their dependents (contacts / leads / deals).
const singleDoctypes = [
  { name: 'CRM Organization', label: 'Organizations' },
  { name: 'Contact', label: 'Contacts' },
  { name: 'CRM Lead', label: 'Leads' },
  { name: 'CRM Deal', label: 'Deals' },
]

/**
 * Trigger a browser download by calling the whitelisted API endpoint.
 * Using window.open (not fetch) so Frappe's `type=download` response
 * short-circuits into a native "save as" dialog — no blob juggling.
 */
function downloadTemplate(doctype) {
  const url =
    `/api/method/crm.api.data_import.download_template` +
    `?doctype=${encodeURIComponent(doctype)}`
  window.open(url, '_blank')
}

function downloadAllTemplatesZip() {
  window.open(
    '/api/method/crm.api.data_import.download_all_templates_zip',
    '_blank',
  )
}

usePageMeta(() => {
  return {
    title: __('Data Import'),
  }
})
</script>
