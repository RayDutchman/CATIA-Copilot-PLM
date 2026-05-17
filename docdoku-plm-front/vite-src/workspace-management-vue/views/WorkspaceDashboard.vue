<template>
  <!-- 工作区仪表盘，对应原 workspace-dashboard.html + views/workspace-dashboard.js -->
  <!-- 原版依赖 nvd3/d3，Vue 版用纯 SVG 实现：饼图/实体柱状图/用户柱状图/签出散点图 -->
  <div class="actions well">
    <button class="btn btn-default" @click="$router.push('/')">{{ t('BACK') }}</button>
  </div>

  <div class="margin">
    <h3>{{ t('DASHBOARD') }}</h3>

    <div v-if="loading" class="charts workspace-chart-container">
      <p class="muted">Loading…</p>
    </div>

    <div v-else class="charts workspace-chart-container">

      <!-- ① 磁盘用量：SVG 饼图（左饼 + 右图例，对应原版 nvd3 pieChart） -->
      <div class="chart well-large well workspace-chart chart-anim">
        <h3>{{ t('DISK_USAGE') }}</h3>

        <template v-if="diskUsageItems.length">
          <!-- 饼图 + 图例两列布局 -->
          <div style="display:flex; align-items:flex-start; gap:16px;">
            <!-- 饼图 SVG：充满左半列 -->
            <svg viewBox="0 0 200 200" style="flex:0 0 auto; width:min(100%,200px); height:auto; display:block;">
              <g v-for="slice in pieSlices" :key="slice.key">
                <path :d="slice.d" :fill="slice.color" stroke="#fff" stroke-width="2" />
                <text
                  v-if="slice.pct >= 6"
                  :x="slice.lx"
                  :y="slice.ly"
                  text-anchor="middle"
                  dominant-baseline="central"
                  font-size="11"
                  fill="#fff"
                  font-weight="bold"
                >{{ slice.pct }}%</text>
              </g>
            </svg>
            <!-- 图例列 -->
            <ul class="unstyled" style="margin:0; padding:0; font-size:13px; flex:1;">
              <li v-for="slice in pieSlices" :key="slice.key" style="display:flex; align-items:center; margin:4px 0;">
                <span :style="{ background: slice.color, display:'inline-block', width:'14px', height:'14px', marginRight:'8px', borderRadius:'2px', flexShrink:0 }"></span>
                <span>{{ slice.key }}<br/><small class="muted">{{ formatBytes(slice.value) }}</small></span>
              </li>
            </ul>
          </div>
          <p style="margin-top:8px; font-size:13px;">{{ t('DISK_USAGE_TOTAL') }}: <strong>{{ formatBytes(totalDiskUsage) }}</strong></p>
        </template>
        <p v-else class="muted">{{ t('NO_DATA') }}</p>
      </div>

      <!-- ② 实体统计：SVG 柱状图 -->
      <div class="chart well-large well workspace-chart chart-anim">
        <h3>{{ t('ENTITIES') }}</h3>
        <template v-if="stats">
          <svg viewBox="0 0 300 220" width="100%" style="display:block; overflow:visible;">
            <!-- y 轴刻度线 -->
            <g v-for="tick in entityYTicks" :key="tick.y">
              <line :x1="CHART_PAD_L" :y1="tick.sy" :x2="CHART_W - CHART_PAD_R" :y2="tick.sy" stroke="#E5E9F0" stroke-width="1" stroke-dasharray="3,3" />
              <text :x="CHART_PAD_L - 4" :y="tick.sy + 4" text-anchor="end" font-size="10" fill="#888">{{ tick.y }}</text>
            </g>
            <!-- 柱子 -->
            <g v-for="bar in entityBars" :key="bar.key">
              <rect :x="bar.x" :y="bar.y" :width="bar.w" :height="bar.h" :fill="bar.color" rx="2" />
              <text :x="bar.x + bar.w/2" :y="bar.y - 5" text-anchor="middle" font-size="12" font-weight="bold" fill="#434C5E">{{ bar.value }}</text>
              <text :x="bar.x + bar.w/2" :y="CHART_BASE + 16" text-anchor="middle" font-size="11" fill="#4C566A">{{ t(bar.key) }}</text>
            </g>
            <!-- x 轴基线 -->
            <line :x1="CHART_PAD_L" :y1="CHART_BASE" :x2="CHART_W - CHART_PAD_R" :y2="CHART_BASE" stroke="#D8DEE9" stroke-width="1.5" />
          </svg>
        </template>
        <p v-else class="muted">{{ t('NO_DATA') }}</p>
      </div>

      <!-- ③ 用户统计：SVG 柱状图（对应原版 constructUsersCharts / users_chart）-->
      <div class="chart well-large well workspace-chart chart-anim">
        <h3>{{ t('USERS') }}</h3>
        <template v-if="userBars.length">
          <svg viewBox="0 0 380 220" width="100%" style="display:block; overflow:visible;">
            <!-- y 轴刻度线 -->
            <g v-for="tick in userYTicks" :key="tick.y">
              <line :x1="CHART_PAD_L" :y1="tick.sy" :x2="380 - CHART_PAD_R" :y2="tick.sy" stroke="#E5E9F0" stroke-width="1" stroke-dasharray="3,3" />
              <text :x="CHART_PAD_L - 4" :y="tick.sy + 4" text-anchor="end" font-size="10" fill="#888">{{ tick.y }}</text>
            </g>
            <!-- 柱子 -->
            <g v-for="bar in userBars" :key="bar.key">
              <rect :x="bar.x" :y="bar.y" :width="bar.w" :height="bar.h" :fill="bar.color" rx="2" />
              <text :x="bar.x + bar.w/2" :y="bar.y - 5" text-anchor="middle" font-size="12" font-weight="bold" fill="#434C5E">{{ bar.value }}</text>
              <text :x="bar.x + bar.w/2" :y="CHART_BASE + 16" text-anchor="middle" font-size="10" fill="#4C566A">{{ t(bar.key) }}</text>
            </g>
            <!-- x 轴基线 -->
            <line :x1="CHART_PAD_L" :y1="CHART_BASE" :x2="380 - CHART_PAD_R" :y2="CHART_BASE" stroke="#D8DEE9" stroke-width="1.5" />
          </svg>
        </template>
        <p v-else class="muted">{{ t('NO_DATA') }}</p>
      </div>

      <!-- ④ 已签出文档：散点图（对应原版 cod_chart，x=天数，y=数量，按用户分色） -->
      <div class="chart well-large well workspace-chart large-chart chart-anim">
        <h3>{{ t('CHECKED_OUT_DOCUMENTS') }}</h3>
        <p>{{ t('TOTAL') }}: <strong>{{ checkedOutDocsTotal }}</strong></p>
        <template v-if="codScatterSeries.length">
          <ScatterChart
            :series="codScatterSeries"
            :colors="COLORS"
            :x-label="t('CHART_AXIS_DAYS_NUMBER')"
            :y-label="t('CHART_AXIS_DOCUMENTS_NUMBER')"
          />
          <!-- 用户图例 -->
          <div style="margin-top:6px; font-size:11px; display:flex; flex-wrap:wrap; gap:8px;">
            <span v-for="(s, i) in codScatterSeries" :key="s.user" style="display:flex; align-items:center;">
              <span :style="{ background: COLORS[i % COLORS.length], width:'10px', height:'10px', borderRadius:'50%', display:'inline-block', marginRight:'4px' }"></span>
              {{ s.user }}
            </span>
          </div>
        </template>
        <p v-else class="muted">{{ t('NO_DATA') }}</p>
      </div>

      <!-- ⑤ 已签出零件：散点图（对应原版 cop_chart） -->
      <div class="chart well-large well workspace-chart large-chart chart-anim">
        <h3>{{ t('CHECKED_OUT_PARTS') }}</h3>
        <p>{{ t('TOTAL') }}: <strong>{{ checkedOutPartsTotal }}</strong></p>
        <template v-if="copScatterSeries.length">
          <ScatterChart
            :series="copScatterSeries"
            :colors="COLORS"
            :x-label="t('CHART_AXIS_DAYS_NUMBER')"
            :y-label="t('CHART_AXIS_PARTS_NUMBER')"
          />
          <div style="margin-top:6px; font-size:11px; display:flex; flex-wrap:wrap; gap:8px;">
            <span v-for="(s, i) in copScatterSeries" :key="s.user" style="display:flex; align-items:center;">
              <span :style="{ background: COLORS[i % COLORS.length], width:'10px', height:'10px', borderRadius:'50%', display:'inline-block', marginRight:'4px' }"></span>
              {{ s.user }}
            </span>
          </div>
        </template>
        <p v-else class="muted">{{ t('NO_DATA') }}</p>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, defineComponent, h } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useApi } from '../../vue-common/composables/useApi.js'

const { t }  = useI18n()
const route  = useRoute()
const api    = useApi()

const workspaceId = computed(() => route.params.workspaceId)

// ── 状态 ──────────────────────────────────────────────────
const loading     = ref(true)
const diskUsage   = ref(null)
const stats       = ref(null)
const usersStats  = ref(null)
const codRaw      = ref(null)   // checked-out-documents-stats 原始数据
const copRaw      = ref(null)   // checked-out-parts-stats 原始数据

// Nord 调色盘
const COLORS = ['#5E81AC', '#88C0D0', '#A3BE8C', '#EBCB8B', '#D08770', '#BF616A', '#B48EAD', '#81A1C1']

// 柱状图共用布局常量（viewBox 坐标系）
const CHART_W      = 300   // entity 图 viewBox 宽度
const CHART_PAD_L  = 28    // 左边 y 轴标签空间
const CHART_PAD_R  = 10    // 右边留白
const CHART_BASE   = 185   // x 轴基线 y 坐标（chart 高 220，留底部 35px 给标签）
const CHART_HEIGHT = 150   // 柱子最大高度

// ── 磁盘用量饼图 ──────────────────────────────────────────

const diskUsageItems = computed(() => {
  if (!diskUsage.value) return []
  return Object.entries(diskUsage.value)
    .filter(([, v]) => typeof v === 'number' && v > 0)
    .map(([k, v]) => ({ key: k, value: v }))
})

const totalDiskUsage = computed(() =>
  diskUsageItems.value.reduce((s, i) => s + i.value, 0)
)

const pieSlices = computed(() => {
  const items = diskUsageItems.value
  if (!items.length) return []
  const total = totalDiskUsage.value
  const cx = 100, cy = 100, r = 80
  let angle = -Math.PI / 2
  return items.map((item, idx) => {
    const frac = item.value / total
    const sweep = frac * 2 * Math.PI
    const startAngle = angle; angle += sweep
    const x1 = cx + r * Math.cos(startAngle)
    const y1 = cy + r * Math.sin(startAngle)
    const x2 = cx + r * Math.cos(angle)
    const y2 = cy + r * Math.sin(angle)
    const largeArc = sweep > Math.PI ? 1 : 0
    let d
    if (items.length === 1) {
      d = `M ${cx+r} ${cy} A ${r} ${r} 0 1 1 ${cx-r} ${cy} A ${r} ${r} 0 1 1 ${cx+r} ${cy} Z`
    } else {
      d = `M ${cx} ${cy} L ${x1.toFixed(2)} ${y1.toFixed(2)} A ${r} ${r} 0 ${largeArc} 1 ${x2.toFixed(2)} ${y2.toFixed(2)} Z`
    }
    const midAngle = startAngle + sweep / 2
    const lr = r * 0.55
    return {
      d, color: COLORS[idx % COLORS.length],
      key: item.key, value: item.value,
      pct: Math.round(frac * 100),
      lx: (cx + lr * Math.cos(midAngle)).toFixed(2),
      ly: (cy + lr * Math.sin(midAngle)).toFixed(2),
    }
  })
})

// ── 实体柱状图 ────────────────────────────────────────────

const entityBars = computed(() => {
  if (!stats.value) return []
  const items = [
    { key: 'USERS',     value: stats.value.users     || 0 },
    { key: 'DOCUMENTS', value: stats.value.documents  || 0 },
    { key: 'PARTS',     value: stats.value.parts      || 0 },
    { key: 'PRODUCTS',  value: stats.value.products   || 0 },
  ]
  return buildBars(items, { totalW: CHART_W, padL: CHART_PAD_L, padR: CHART_PAD_R, barW: 42, gapX: 14 })
})

/** entity 图 y 轴刻度（4 ~ 5 条线） */
const entityYTicks = computed(() => buildYTicks(entityBars.value))

// ── 用户统计柱状图（users-stats API） ─────────────────────
// 字段：activeusers / inactiveusers / groups / activegroups / inactivegroups
const USER_STATS_KEYS = [
  { key: 'activeusers',   i18nKey: 'ACTIVE_USERS'    },
  { key: 'inactiveusers', i18nKey: 'INACTIVE_USERS'  },
  { key: 'groups',        i18nKey: 'GROUPS'           },
  { key: 'activegroups',  i18nKey: 'ACTIVE_GROUPS'   },
  { key: 'inactivegroups',i18nKey: 'INACTIVE_GROUPS' },
]

const userBars = computed(() => {
  if (!usersStats.value) return []
  const items = USER_STATS_KEYS
    .filter(({ key }) => usersStats.value[key] !== undefined)
    .map(({ key, i18nKey }) => ({ key: i18nKey, value: usersStats.value[key] || 0 }))
  if (!items.length) return []
  return buildBars(items, { totalW: 380, padL: CHART_PAD_L, padR: CHART_PAD_R, barW: 48, gapX: 12 })
})

/** user 图 y 轴刻度 */
const userYTicks = computed(() => buildYTicks(userBars.value))

/** 通用柱状图计算（返回每柱的 SVG 坐标和颜色） */
function buildBars(items, { totalW, padL, padR, barW, gapX }) {
  const maxVal = Math.max(...items.map(i => i.value), 1)
  return items.map((item, i) => {
    const h = Math.max(2, Math.round((item.value / maxVal) * CHART_HEIGHT))
    const x = padL + gapX + i * (barW + gapX)
    const y = CHART_BASE - h
    return { ...item, x, y, h, w: barW, color: COLORS[i % COLORS.length] }
  })
}

/** 生成 y 轴刻度：取 bars 中最大值，分 4 段 */
function buildYTicks(bars) {
  if (!bars.length) return []
  const maxVal = Math.max(...bars.map(b => b.value), 1)
  const step = Math.ceil(maxVal / 4)
  const ticks = []
  for (let v = step; v <= maxVal; v += step) {
    const sy = CHART_BASE - Math.round((v / maxVal) * CHART_HEIGHT)
    ticks.push({ y: v, sy })
  }
  return ticks
}

// ── 签出文档 / 零件散点数据 ───────────────────────────────
// 原版算法：对每个用户，按天（x=days since checkout, y=count）聚合，点大小 = count
const MAX_DAYS = 30

function buildScatterSeries(raw) {
  if (!raw || typeof raw !== 'object') return []
  const series = []
  let total = 0
  for (const [user, items] of Object.entries(raw)) {
    if (!Array.isArray(items)) continue
    const dayMap = {}
    for (const item of items) {
      const ts = item.date || item.checkOutDate || 0
      let days = Math.floor(((Date.now() - ts) / 1000 / 60 / 60 / 24))
      days = Math.min(days < 0 ? 0 : days + 1, MAX_DAYS)
      dayMap[days] = (dayMap[days] || 0) + 1
      total++
    }
    const values = Object.entries(dayMap)
      .filter(([, cnt]) => cnt > 0)
      .map(([day, cnt]) => ({ x: Number(day), y: cnt, size: cnt }))
    if (values.length) series.push({ user, values })
  }
  return { series, total }
}

const _cod = computed(() => buildScatterSeries(codRaw.value))
const _cop = computed(() => buildScatterSeries(copRaw.value))

const codScatterSeries  = computed(() => _cod.value.series || [])
const checkedOutDocsTotal = computed(() => _cod.value.total || 0)
const copScatterSeries  = computed(() => _cop.value.series || [])
const checkedOutPartsTotal = computed(() => _cop.value.total || 0)

// ── 辅助函数 ──────────────────────────────────────────────

function formatBytes(bytes) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let i = 0, n = bytes
  while (n >= 1024 && i < units.length - 1) { n /= 1024; i++ }
  return n.toFixed(1) + ' ' + units[i]
}

// ── 生命周期 ──────────────────────────────────────────────
onMounted(async () => {
  try {
    const [du, st, us, cod, cop] = await Promise.allSettled([
      api.get(`/workspaces/${workspaceId.value}/disk-usage-stats`),
      api.get(`/workspaces/${workspaceId.value}/stats-overview`),
      api.get(`/workspaces/${workspaceId.value}/users-stats`),
      api.get(`/workspaces/${workspaceId.value}/checked-out-documents-stats`),
      api.get(`/workspaces/${workspaceId.value}/checked-out-parts-stats`),
    ])
    if (du.status  === 'fulfilled') diskUsage.value  = du.value
    if (st.status  === 'fulfilled') stats.value      = st.value
    if (us.status  === 'fulfilled') usersStats.value = us.value
    if (cod.status === 'fulfilled') codRaw.value     = cod.value
    if (cop.status === 'fulfilled') copRaw.value     = cop.value
  } finally {
    loading.value = false
  }
})
</script>

<!-- ── 散点图子组件（纯 SVG，内联 script） ───────────────── -->
<script>
/**
 * ScatterChart：SVG 散点图
 * props: series=[{user, values:[{x,y,size}]}], colors, xLabel, yLabel
 * viewBox: 280×160，左边 30px 为 y 轴标签，底部 20px 为 x 轴标签
 */
export const ScatterChart = {
  name: 'ScatterChart',
  props: {
    series:  { type: Array,  default: () => [] },
    colors:  { type: Array,  default: () => [] },
    xLabel:  { type: String, default: '' },
    yLabel:  { type: String, default: '' },
  },
  setup(props) {
    const W = 280, H = 140
    const padL = 30, padB = 20, padR = 10, padT = 10
    const plotW = W - padL - padR
    const plotH = H - padT - padB

    const allPoints = () => props.series.flatMap(s => s.values)
    const maxX = () => Math.max(...allPoints().map(p => p.x), 30)
    const maxY = () => Math.max(...allPoints().map(p => p.y), 1)

    const px = (x) => padL + (x / maxX()) * plotW
    const py = (y) => padT + plotH - (y / maxY()) * plotH
    const pr = (size) => Math.min(2 + size * 2, 10)

    return () => {
      const nodes = []

      // 轴
      nodes.push(
        h('line', { x1: padL, y1: padT, x2: padL, y2: padT + plotH, stroke: '#D8DEE9', 'stroke-width': 1 }),
        h('line', { x1: padL, y1: padT + plotH, x2: padL + plotW, y2: padT + plotH, stroke: '#D8DEE9', 'stroke-width': 1 }),
      )

      // 散点
      props.series.forEach((s, si) => {
        const color = props.colors[si % props.colors.length]
        s.values.forEach(pt => {
          nodes.push(
            h('circle', {
              cx: px(pt.x),
              cy: py(pt.y),
              r:  pr(pt.size),
              fill: color,
              'fill-opacity': 0.8,
            })
          )
        })
      })

      // 轴标签
      nodes.push(
        h('text', { x: padL + plotW / 2, y: H, 'text-anchor': 'middle', 'font-size': 9, fill: '#4C566A' }, props.xLabel),
        h('text', {
          x: 8, y: padT + plotH / 2,
          'text-anchor': 'middle',
          'font-size': 9,
          fill: '#4C566A',
          transform: `rotate(-90, 8, ${padT + plotH / 2})`,
        }, props.yLabel),
      )

      return h('svg', {
        viewBox: `0 0 ${W} ${H}`,
        width: '100%',
        style: 'display:block; overflow:visible;',
      }, nodes)
    }
  }
}
</script>

<style scoped>
/* SVG 图表淡入动画 */
@keyframes chartFadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to   { opacity: 1; transform: translateY(0); }
}
.chart-anim {
  animation: chartFadeIn 0.5s ease both;
}
/* 为每张图错开动画延迟 */
.chart-anim:nth-child(1) { animation-delay: 0.05s; }
.chart-anim:nth-child(2) { animation-delay: 0.15s; }
.chart-anim:nth-child(3) { animation-delay: 0.25s; }
.chart-anim:nth-child(4) { animation-delay: 0.35s; }
.chart-anim:nth-child(5) { animation-delay: 0.45s; }
</style>
