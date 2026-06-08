import { useState, useEffect, useCallback } from 'react'
import { MOCK_FSS_RATES } from '../data/mockData'
import SkeletonRows from '../components/SkeletonRows'
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
  // productCode: FSS 상품코드 직접 지정 (이름 매칭보다 정확) — F35605=주택담보대출(일반형), F35405=주택담보대출(한도형)
  { id: 'samsung-life', name: '삼성생명', match: '삼성생명', productCode: 'F35605', colorHex: '#6366f1' },
  { id: 'hanwha',       name: '한화생명', match: '한화생명',  colorHex: '#ef4444' },
  { id: 'kyobo',        name: '교보생명', match: '교보생명',  colorHex: '#10b981' },
  { id: 'samsung-fire', name: '삼성화재', match: '삼성화재',  colorHex: '#e11d48' },
]

// FSS API 금리유형 → 화면 표시명 정규화
// 혼합금리(C)는 변동금리로 표시 (삼성생명 등 보험사 주담대 특성)
const RATE_TYPE_NORMALIZE = {
  '고정금리': '고정금리',
  '혼합금리': '변동금리',
  '변동금리': '변동금리',
}
const RATE_TYPE_ORDER = ['고정금리', '변동금리']

function parseRates(baseList, optionList, config) {
  return config.map((cfg) => {
    let allProds = baseList.filter((p) => p.kor_co_nm.includes(cfg.match))

    // productCode 직접 지정 시 해당 상품코드만 사용 — F35605(일반형)만 남겨 F35405(한도형) 제거
    if (cfg.productCode) {
      const direct = allProds.filter((p) => p.fin_prdt_cd === cfg.productCode)
      if (direct.length > 0) allProds = direct
    }
    // preferProduct 지정 시 해당 상품명 포함 상품 우선 사용 (productCode 없을 때 폴백)
    else if (cfg.preferProduct) {
      const preferred = allProds.filter((p) => p.fin_prdt_nm.includes(cfg.preferProduct))
      if (preferred.length > 0) allProds = preferred
    }

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
      // FSS 원본 유형을 정규화된 표시명으로 변환 (혼합금리 → 변동금리)
      const rawType = o.lend_rate_type_nm
      const type    = RATE_TYPE_NORMALIZE[rawType] ?? rawType
      if (!type) continue
      if (!byType[type]) byType[type] = { mins: [], maxs: [], avgs: [] }
      if (o.lend_rate_min != null && o.lend_rate_min > 0) byType[type].mins.push(o.lend_rate_min)
      if (o.lend_rate_max != null && o.lend_rate_max > 0) byType[type].maxs.push(o.lend_rate_max)
      if (o.lend_rate_avg != null && o.lend_rate_avg > 0) byType[type].avgs.push(o.lend_rate_avg)
    }

    const rateTypes = RATE_TYPE_ORDER
      .filter((t) => byType[t])
      .map((t) => ({
        type:    t,
        minRate: byType[t].mins.length ? Math.min(...byType[t].mins) : null,
        maxRate: byType[t].maxs.length ? Math.max(...byType[t].maxs) : null,
      }))

    const product = products[0]?.fin_prdt_nm ?? '주택담보대출'
    return { id: cfg.id, name: cfg.name, colorHex: cfg.colorHex, product, rateTypes }
  })
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
            {rateTypes.map(({ type, minRate, maxRate }) => (
              <div key={type} className="flex items-center gap-3">
                <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded shrink-0 ${type === '고정금리' ? 'bg-blue-100 text-blue-700' : 'bg-amber-100 text-amber-700'}`}>
                  {type}
                </span>
                <div className="flex items-center gap-2 text-xs tabular-nums">
                  <span className="text-slate-400">최저</span>
                  <span className="font-bold text-emerald-600">{minRate != null ? `${minRate.toFixed(2)}%` : '—'}</span>
                  <span className="text-slate-300">|</span>
                  <span className="text-slate-400">최고</span>
                  <span className="font-bold text-rose-500">{maxRate != null ? `${maxRate.toFixed(2)}%` : '—'}</span>
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
  const [loading, setLoading] = useState(true)
  const [statusMsg, setStatusMsg] = useState(null)
  const [statusType, setStatusType] = useState('warn')

  const load = useCallback(async () => {
    try {
      setLoading(true)
      const params = (grp) =>
        `${FSS_API_BASE}?auth=${FSS_API_KEY}&topFinGrpNo=${grp}&pageNo=1`

      const [banksRes, insRes] = await Promise.all([
        fetch(params('020000'), { signal: AbortSignal.timeout(10000) }),
        fetch(params('050000'), { signal: AbortSignal.timeout(10000) }),
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
      setStatusMsg(null)
    } catch (err) {
      console.warn('FSS API 연결 실패:', err.message)
      setData(MOCK_FSS_RATES)
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
        subtitle={`매월 공시 · FSS API 실시간${data ? ` · ${data.updatedAt}` : ''}`}
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

        <div className="flex flex-wrap items-center gap-4 justify-center text-xs text-slate-500 pb-2">
          <span>금융감독원 금융상품 통합비교공시 기준 · 매월 1회 공시 (FSS API 실시간 조회)</span>
        </div>
      </div>
    </div>
  )
}
