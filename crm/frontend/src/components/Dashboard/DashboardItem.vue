<template>
  <div class="h-full w-full">
    <div
      v-if="item.type == 'number_chart'"
      class="flex h-full w-full rounded shadow overflow-hidden cursor-pointer"
    >
      <Tooltip :text="__(item.data.tooltip)">
        <NumberChart
          v-if="item.data"
          :key="index"
          class="!items-start"
          :config="item.data"
        />
      </Tooltip>
    </div>
    <div
      v-else-if="item.type == 'spacer'"
      class="rounded bg-surface-base h-full overflow-hidden text-ink-gray-5 flex items-center justify-center"
      :class="editing ? 'border border-dashed border-outline-gray-2' : ''"
    >
      {{ editing ? __('Spacer') : '' }}
    </div>
    <div
      v-else-if="item.type == 'axis_chart'"
      class="h-full w-full rounded-md bg-surface-base shadow"
    >
      <AxisChart v-if="item.data" :config="translatedConfig" />
    </div>
    <div
      v-else-if="item.type == 'donut_chart'"
      class="h-full w-full rounded-md bg-surface-base shadow overflow-hidden"
    >
      <DonutChart v-if="item.data" :config="translatedConfig" />
    </div>
  </div>
</template>
<script setup>
import { AxisChart, DonutChart, NumberChart, Tooltip } from 'frappe-ui'
import { computed } from 'vue'

const props = defineProps({
  index: { type: Number, required: true },
  item: { type: Object, required: true },
  editing: { type: Boolean, default: false },
})

// Translate an axis/donut chart config on the fly. Two channels of English
// leakage from the backend need translating on the client:
//
// 1. series[i].name  — e.g. "leads", "won_deals", "forecasted". frappe-ui
//    uses this string as the legend label AND as the key into each data row,
//    so if we rename the series we must also rename the matching key on
//    every row (and on any axis whose `key` points at it).
//
// 2. Category labels inside data[] — e.g. donut charts render one slice per
//    row, using row[xAxis.key] as the slice label. Those values are raw
//    DocType record names ("Cold Calling", "Reference", "Prospecting" …).
//    We translate the value itself, so "Cold Calling (33%)" becomes
//    "电话陌拜 (33%)" once the po file has that entry.
const translatedConfig = computed(() => {
  const cfg = props.item?.data
  if (!cfg || !Array.isArray(cfg.data)) {
    return cfg
  }

  const remap = {}
  const newSeries = Array.isArray(cfg.series)
    ? cfg.series.map((s) => {
        const label = __(s.name)
        remap[s.name] = label
        return { ...s, name: label }
      })
    : cfg.series

  // Which columns in data[] hold category labels (as opposed to numeric
  // measures)? xAxis.key is the primary one for donut/bar charts; we also
  // translate any string value that isn't a numeric measure column.
  const measureKeys = new Set(Object.keys(remap))
  const labelKeys = new Set()
  if (cfg.xAxis?.key) labelKeys.add(cfg.xAxis.key)

  const newData = cfg.data.map((row) => {
    const copy = { ...row }
    // Rename measure columns to their translated series name.
    for (const [oldKey, newKey] of Object.entries(remap)) {
      if (oldKey !== newKey && oldKey in copy) {
        copy[newKey] = copy[oldKey]
        delete copy[oldKey]
      }
    }
    // Translate string values in label columns (record names like
    // "Cold Calling" → "电话陌拜"). Skip numeric measures.
    for (const key of Object.keys(copy)) {
      const isMeasure = measureKeys.has(key) || (remap[key] && key !== remap[key])
      if (isMeasure) continue
      const val = copy[key]
      if (typeof val === 'string' && val) {
        copy[key] = __(val)
      }
    }
    return copy
  })

  // Adjust axis keys that referenced a renamed measure column.
  const remapAxis = (axis) => {
    if (!axis || typeof axis !== 'object') return axis
    if (axis.key && remap[axis.key]) {
      return { ...axis, key: remap[axis.key] }
    }
    return axis
  }

  return {
    ...cfg,
    series: newSeries,
    data: newData,
    xAxis: remapAxis(cfg.xAxis),
    yAxis: remapAxis(cfg.yAxis),
    y2Axis: remapAxis(cfg.y2Axis),
  }
})
</script>
