import { useState, useEffect, useCallback } from 'react'
import { MOCK_FSS_RATES } from '../data/mockData'
import SkeletonRows from '../components/SkeletonRows'
import RateChart from '../components/RateChart'
import PageHeader from '../components/PageHeader'

const FSS_API_KEY = '736b1d88e7160ca02d43154c35ca6bc6'
const FSS_API_BASE = '/api/fss/mortgageLoanProductsSearch.json'

const BANK_CONFIG = [
  { id: 'kb',      name: 'KB국민은행',  match: '국민은행',  colorHex: '#f59e0b' },
  { id: 'shinhan', name: '신한은행',    match: '신한은행',  colorHex: '#f97316' },
  { id: 'hana',    name: '하나은행',    match: '하나은행',  colorHex: '#14b8a6' },
  { id: 'woori',   name: '우리은행',    match: '우리은행',  colorHex: '#3b82f6' },
  { id: 'nh',      name: 'NH농협은행',  match: '농협은행',  colorHex: '#22c55e' },
]

const INSURANCE_CONFIG = [
  { id: 'samsung-life', name: '삼성생명', match: '삼성생명',  colorHex: '#6366f1' },
  { id: 'hanwha',       name: '한화생명', match: '한화생명',  colorHex: '#ef4444' },
  { id: 'kyobo',        name: '교보생명', match: '교보생명',  colorHex: '#10b981' },
  { id: 'samsung-fire', name: '삼성화재', match: '삼성화재',  colorHex: '#e11d48' },
]

const RATE_TYPE_ORDER = ['고정금리', '변동금리']

function parseRates(baseList, optionList, config) {
  return config.map((cfg) => {
    const allProds = baseList.filter((p) => p.kor_co_nm.includes(cfg.match))
    // '(아파트)' 포함 상품 우선 (신한은행 등 여러 상품 분리 대응)
    const aptProds = allProds.filter((p) => p.fin_prdt_nm.includes('(아파트)'))
    const products = aptProds.length > 0 ? aptProds : allProds
    const codes    = new Set(products.map((p) => p.fin_prdt_cd))

    // 조건: mrtg_type=A(아파트) + rpay_type=D(분할상환) — 사용자 지정 기본 조건
    let opts = optionList.filter(
      (o) => codes.has(o.fin_prdt_cd) && o.mrtg_type === 'A' && o.rpay_type === 'D'
    )
    if (opts.length === 0)
      opts = optionList.filter((o) => codes.has(o.fin_prdt_cd) && o.mrtg_type === 'A')
    if (opts.length === 0)
      opts = optionList.filter((o) => codes.has(o.fin_prdt_cd))

    if (opts.length === 0) return { ...cfg, product: '주택담보대출', rateTypes: [] }

    const byType = {}
    for (const o of opts) {
      const type = o.lend_rate_type_nm
      if (!type) continue
      if (!byType[type]) byType[type] = { mins: [], maxs: [], avgs: [] }
      if (o.lend_rate_min != null && o.lend_rate_min > 0) byType[type].mins.push(o.lend_rate_min)
      if (o.lend_rate_max != null && o.lend_rate_max > 0) byType[type].maxs.push(o.lend_rate_max)
      if (o.lend_rate_avg != null && o.lend_rate_avg > 0) byType[type].avgs.push(o.lend_rate_avg)
    }

    const rateTypes = RATE_TYPE_ORDER
      .filter((t) => byType[t])
      .map((t) => {
        const minRate   = byType[t].mins.length ? Math.min(...byType[t].mins) : null
        const avgRate   = byType[t].avgs.length ? Math.min(...byType[t].avgs) : null
        // 변동폭: 현재 최저금리 - 전월 평균금리
        const minChange = minRate != null && avgRate != null
          ? Math.round((minRate - avgRate) * 100) / 100
          : null
        return {
          type: t,
          minRate,
          maxRate:   byType[t].maxs.length ? Math.max(...byType[t].maxs) : null,
          minChange,
        }
      })

    const product = products[0]?.fin_prdt_nm ?? '주택담보대출'
    return { id: cfg.id, name: cfg.name, colorHex: cfg.colorHex, product, rateTypes }
  })
}

const BANK_SERIES = [
  { key: 'kb',     name: 'KB국민',  color: '#f59e0b' },
  { key: 'shinhan',name: '신한',    color: '#3b82f6' },
  { key: 'hana',   name: '하나',    color: '#10b981' },
  { key: 'woori',  name: '우리',    color: '#8b5cf6' },
  { key: 'nh',     name: '농협',    color: '#f97316' },
]
const INSURANCE_SERIES = [
  { key: 'samsungLife', name: '삼성생명', color: '#6366f1' },
  { key: 'hanwha',      name: '한화생명', color: '#f43f5e' },
  { key: 'kyobo',       name: '교보생명', color: '#0ea5e9' },
  { key: 'samsungFire', name: '삼성화재', color: '#14b8a6' },
]

function ChangeChip({ value }) {
  if (value == null || value === 0) return null
  return value > 0
    ? <span className="text-rose-500 text-[10px] font-semibold">▲ +{value.toFixed(2)}%</span>
    : <span className="text-blue-500 text-[10px] font-semibold">▼ {value.toFixed(2)}%</span>
}

function FSSRateCard({ name, colorHex, product, rateTypes }) {
  return (
    <div className="flex items-start py-4 px-5 border-b border-slate-100 last:border-0 hover:bg-slate-50 transition-colors gap-3">
      <div className="w-1.5 rounded-full shrink-0 mt-1" style={{ backgroundColor: colorHex, height: rateTypes.length > 1 ? '52px' : '36px' }} />
      <div className="flex-1 min-w-0">
        <div className="font-semibold text-slate-800 text-sm leading-tight">{name}</div>
        <div className="text-xs text-slate-400 truncate mt-0.5 mb-2">{product}</div>
        {rateTypes.length === 0 ? (
          <div className="text-xs text-slate-400">데이터 없음</div>
        ) : (
          <div className="space-y-2">
            {rateTypes.map(({ type, minRate, maxRate, minChange }) => (
              <div key={type} className="flex items-start gap-3">
                <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded shrink-0 mt-0.5 ${type === '고정금리' ? 'bg-blue-100 text-blue-700' : 'bg-amber-100 text-amber-700'}`}>
                  {type}
                </span>
                <div className="flex flex-col gap-0.5">
                  <div className="flex items-center gap-2 text-xs tabular-nums">
                    <span className="text-slate-400">최저</span>
                    <span className="font-bold text-emerald-600">{minRate != null ? `${minRate.toFixed(2)}%` : '—'}</span>
                    <span className="text-slate-300">|</span>
                    <span className="text-slate-400">최고</span>
                    <span className="font-bold text-rose-500">{maxRate != null ? `${maxRate.toFixed(2)}%` : '—'}</span>
                  </div>
                  {minChange != null && minChange !== 0 && (
                    <div className="flex items-center gap-1">
                      <span className="text-[10px] text-slate-400">전월比</span>
                      <ChangeChip value={minChange} />
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function SectionPanel({ title, subtitle, children }) {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
      <div className="px-5 py-4 bg-slate-50 border-b border-slate-200 flex items-baseline justify-between gap-2">
        <h2 className="font-bold text-slate-800">{title}</h2>
        <span className="text-xs text-slate-400 shrink-0">{subtitle}</span>
      </div>
      <div>{children}</div>
    </div>
  )
}

function StatusBanner({ type, message }) {
  if (!message) return null
  const styles = {
    warn: 'bg-amber-50 border-amber-200 text-amber-700',
    error: 'bg-rose-50 border-rose-200 text-rose-700',
  }
  const icon = { warn: '⚠️', error: '❌' }
  return (
    <div className={`flex items-center gap-2 border rounded-xl px-4 py-2.5 text-sm ${styles[type]}`}>
      <span>{icon[type]}</span>
      <span>{message}</span>
    </div>
  )
}

export default function FSSView({ onBack }) {
  const [data, setData] = useState(null)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [statusMsg, setStatusMsg] = useState(null)
  const [statusType, setStatusType] = useState('warn')

  const load = useCallback(async () => {
    try {
      setLoading(true)
      const params = (grp) =>
        `${FSS_API_BASE}?auth=${FSS_API_KEY}&topFinGrpNo=${grp}&pageNo=1`

      const [banksRes, insRes, fssRes] = await Promise.all([
        fetch(params('020000'), { signal: AbortSignal.timeout(10000) }),
        fetch(params('050000'), { signal: AbortSignal.timeout(10000) }),
        fetch('/fss.json', { cache: 'no-store' }),
      ])
      if (!banksRes.ok) throw new Error(`Banks HTTP ${banksRes.status}`)
      if (!insRes.ok) throw new Error(`Insurance HTTP ${insRes.status}`)

      const [banksJson, insJson] = await Promise.all([banksRes.json(), insRes.json()])

      const banks = parseRates(
        banksJson.result?.baseList ?? [],
        banksJson.result?.optionList ?? [],
        BANK_CONFIG,
      )
      const insurances = parseRates(
        insJson.result?.baseList ?? [],
        insJson.result?.optionList ?? [],
        INSURANCE_CONFIG,
      )

      const now = new Date()
      const updatedAt = `${now.getFullYear()}년 ${now.getMonth() + 1}월 기준`
      setData({ updatedAt, banks, insurances })

      if (fssRes.ok) {
        const fssJson = await fssRes.json()
        setHistory(fssJson.history ?? [])
      }
      setStatusMsg(null)
    } catch (err) {
      console.warn('FSS API 연결 실패:', err.message)
      setData(MOCK_FSS_RATES)
      setHistory([])
      setStatusMsg('API 미연결 상태입니다 — Mock 데이터를 표시하고 있습니다.')
      setStatusType('warn')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  return (
    <div className="min-h-screen bg-slate-50 animate-fade-in">
      <PageHeader
        title="금융감독원 공시 기준"
        subtitle={`월 단위 업데이트${data ? ` · ${data.updatedAt}` : ''}`}
        onBack={onBack}
        onRefresh={load}
        isRefreshing={loading}
        accent="emerald"
      />

      <div className="max-w-screen-xl mx-auto px-5 py-6 space-y-5">
        <StatusBanner type={statusType} message={statusMsg} />

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <SectionPanel title="🏦 은행권" subtitle="국민 · 신한 · 하나 · 우리 · 농협">
            {loading
              ? <SkeletonRows count={5} />
              : data?.banks.map((b) => <FSSRateCard key={b.id} {...b} />)}
          </SectionPanel>

          <SectionPanel title="🛡️ 보험사" subtitle="삼성생명 · 한화생명 · 교보생명 · 삼성화재">
            {loading
              ? <SkeletonRows count={4} />
              : data?.insurances.map((ins) => <FSSRateCard key={ins.id} {...ins} />)}
          </SectionPanel>
        </div>

        {history.length >= 2 ? (
          <RateChart
            bankData={history}
            insuranceData={history}
            bankSeries={BANK_SERIES}
            insuranceSeries={INSURANCE_SERIES}
            xKey="month"
          />
        ) : (
          <div className="bg-white rounded-2xl border border-slate-200 px-6 py-8 text-center text-sm text-slate-400">
            금리 추이 데이터를 수집 중입니다 · 다음 달부터 월별 추이가 표시됩니다
          </div>
        )}

        <div className="flex flex-wrap items-center gap-4 justify-center text-xs text-slate-500 pb-2">
          <span>금융감독원 금융상품 통합비교공시 기준 · 월별 공시 (매일 변경 감지)</span>
        </div>
      </div>
    </div>
  )
}
