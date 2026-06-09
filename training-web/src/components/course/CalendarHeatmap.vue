<script setup lang="ts">
import { computed } from 'vue'

export interface CalendarDay {
  date: string        // "YYYY-MM-DD"
  duration: number    // seconds
  completed: number   // count of completed videos that day
}

const props = defineProps<{
  data: CalendarDay[]
  loading?: boolean
}>()

const emit = defineEmits<{
  dayClick: [day: CalendarDay]
}>()

// Monday = 0, Sunday = 6
const DAY_LABELS = ['一', '二', '三', '四', '五', '六', '日']
const MONTH_NAMES = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']

// Build a map: dateStr -> CalendarDay
const dayMap = computed(() => {
  const map: Record<string, CalendarDay> = {}
  for (const d of props.data) {
    map[d.date] = d
  }
  return map
})

// Build the grid: rows = weekdays (Mon..Sun), columns = weeks
const grid = computed(() => {
  const weeks: CalendarDay[][] = []
  if (props.data.length === 0) return { weeks, monthLabels: [] as { col: number; label: string }[] }

  const first = new Date(props.data[0].date + 'T00:00:00')
  // Align to Monday (start of the ISO week)
  const start = new Date(first)
  const dayOfWeek = start.getDay() // 0=Sun, 1=Mon, ...
  const offset = dayOfWeek === 0 ? -6 : -(dayOfWeek - 1)
  start.setDate(start.getDate() + offset)

  const last = new Date(props.data[props.data.length - 1].date + 'T00:00:00')
  const lastDayOfWeek = last.getDay()
  const endOffset = lastDayOfWeek === 0 ? 0 : (7 - lastDayOfWeek)
  const end = new Date(last)
  end.setDate(end.getDate() + endOffset)

  const monthLabels: { col: number; label: string }[] = []
  let prevMonth = -1
  let colIndex = 0

  const cursor = new Date(start)
  // Build 7 rows, fill column by column
  const rows: CalendarDay[][] = [[], [], [], [], [], [], []]
  while (cursor <= end) {
    const dateStr = cursor.toISOString().slice(0, 10)
    const weekday = cursor.getDay() // 0=Sun
    const rowIdx = weekday === 0 ? 6 : weekday - 1 // Mon=0, Sun=6

    const entry = dayMap.value[dateStr]
    rows[rowIdx].push(entry || { date: dateStr, duration: 0, completed: 0 })

    // Track month change for labels
    const month = cursor.getMonth()
    if (month !== prevMonth) {
      monthLabels.push({ col: colIndex, label: MONTH_NAMES[month] })
      prevMonth = month
    }

    // Move to next day
    cursor.setDate(cursor.getDate() + 1)
    if (rowIdx === 6) colIndex++
  }

  return { weeks: rows, monthLabels }
})

// Duration level: 0=none, 1=<15m, 2=<30m, 3=<60m, 4=>=60m
function durationLevel(seconds: number): number {
  if (seconds <= 0) return 0
  const m = seconds / 60
  if (m < 15) return 1
  if (m < 30) return 2
  if (m < 60) return 3
  return 4
}

function levelClass(seconds: number): string {
  const lv = durationLevel(seconds)
  return `level-${lv}`
}

function formatTooltip(day: CalendarDay): string {
  if (!day || day.duration <= 0) return '暂无学习记录'
  const m = Math.round(day.duration / 60)
  const parts = [`${m} 分钟`]
  if (day.completed > 0) parts.push(`${day.completed} 门课完成`)
  return parts.join(' · ')
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00')
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

function onCellClick(day: CalendarDay) {
  emit('dayClick', day)
}

const LEGEND_LEVELS = [
  { label: '无', class: 'level-0' },
  { label: '<15m', class: 'level-1' },
  { label: '<30m', class: 'level-2' },
  { label: '<60m', class: 'level-3' },
  { label: '≥60m', class: 'level-4' },
]
</script>

<template>
  <div class="calendar-heatmap">
    <van-loading v-if="loading" size="20" class="heatmap-loading" />

    <template v-else-if="data.length > 0">
      <!-- Month labels row -->
      <div class="heatmap-months">
        <span class="month-spacer" />
        <span
          v-for="(ml, idx) in grid.monthLabels"
          :key="idx"
          class="month-label"
          :style="{ gridColumn: ml.col + 2 }"
        >
          {{ ml.label }}
        </span>
      </div>

      <div class="heatmap-body">
        <div class="heatmap-grid">
          <!-- Day labels -->
          <div class="day-labels">
            <span v-for="d in DAY_LABELS" :key="d" class="day-label">{{ d }}</span>
          </div>

          <!-- Cells -->
          <div class="cell-grid">
            <template v-for="(row, ri) in grid.weeks" :key="ri">
              <div
                v-for="(day, ci) in row"
                :key="`${ri}-${ci}`"
                class="heat-cell"
                :class="levelClass(day.duration)"
                :title="`${formatDate(day.date)} · ${formatTooltip(day)}`"
                @click="onCellClick(day)"
              >
                <div v-if="day.completed > 0" class="cell-dot" />
              </div>
            </template>
          </div>
        </div>

        <!-- Legend -->
        <div class="heatmap-legend">
          <span class="legend-label">少</span>
          <span
            v-for="lv in LEGEND_LEVELS"
            :key="lv.class"
            class="legend-cell"
            :class="lv.class"
            :title="lv.label"
          />
          <span class="legend-label">多</span>
        </div>
      </div>
    </template>

    <div v-else class="heatmap-empty">暂无学习记录</div>
  </div>
</template>

<style lang="scss" scoped>
.calendar-heatmap {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.heatmap-loading {
  padding: 24px 0;
}

.heatmap-months {
  display: flex;
  margin-bottom: 4px;
  font-size: 11px;
  color: var(--text-muted);
  position: relative;
}

.month-spacer {
  width: 24px;
  flex-shrink: 0;
}

.month-label {
  position: absolute;
  white-space: nowrap;
}

.heatmap-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.heatmap-grid {
  display: flex;
  gap: 4px;
}

.day-labels {
  display: flex;
  flex-direction: column;
  gap: 3px;
  flex-shrink: 0;
  padding-top: 1px;
}

.day-label {
  width: 24px;
  height: 14px;
  display: flex;
  align-items: center;
  font-size: 11px;
  color: var(--text-muted);
  line-height: 1;
}

.cell-grid {
  display: grid;
  grid-template-rows: repeat(7, 14px);
  grid-auto-flow: column;
  gap: 3px;
}

.heat-cell {
  width: 14px;
  height: 14px;
  border-radius: 2px;
  background: #ebedf0;
  cursor: pointer;
  transition: transform 0.15s;
  display: flex;
  align-items: center;
  justify-content: center;

  &:active {
    transform: scale(1.3);
  }

  &.level-1 {
    background: #c6e8c6;
  }

  &.level-2 {
    background: #6ec76e;
  }

  &.level-3 {
    background: #2ea62e;
  }

  &.level-4 {
    background: #1a7a1a;
  }

  .cell-dot {
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.7);
  }
}

.heatmap-legend {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 3px;
}

.legend-label {
  font-size: 10px;
  color: var(--text-muted);
  margin: 0 2px;
}

.legend-cell {
  width: 12px;
  height: 12px;
  border-radius: 2px;

  &.level-0 { background: #ebedf0; }
  &.level-1 { background: #c6e8c6; }
  &.level-2 { background: #6ec76e; }
  &.level-3 { background: #2ea62e; }
  &.level-4 { background: #1a7a1a; }
}

.heatmap-empty {
  text-align: center;
  padding: 24px 0;
  color: var(--text-muted);
  font-size: 13px;
}
</style>
