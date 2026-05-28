function ChangeIndicator({ value }) {
  if (value === null || value === undefined) return null
  if (value === 0) return <span className="text-slate-400 text-xs leading-none">—</span>
  if (value > 0) {
    return (
      <span className="text-rose-500 text-xs font-semibold leading-none">
        ▲ +{value.toFixed(2)}%
      </span>
    )
  }
  return (
    <span className="text-blue-500 text-xs font-semibold leading-none">
      ▼ {value.toFixed(2)}%
    </span>
  )
}

export default function RateRow({ name, product, minRate, maxRate, minChange, maxChange, colorHex, displayRange }) {
  return (
    <div className="flex items-center py-4 px-5 border-b border-slate-100 last:border-0 hover:bg-slate-50 transition-colors">
      {/* Institution name */}
      <div className="flex items-center gap-3 flex-1 min-w-0 mr-4">
        <div
          className="w-1.5 h-10 rounded-full shrink-0"
          style={{ backgroundColor: colorHex }}
        />
        <div className="min-w-0">
          <div className="font-semibold text-slate-800 text-sm leading-tight">{name}</div>
          <div className="text-xs text-slate-400 truncate mt-0.5">{product}</div>
        </div>
      </div>

      {/* Rates */}
      {displayRange ? (
        <div className="shrink-0 text-right">
          <div className="text-[11px] text-slate-400 font-medium mb-1">제안금리 범위</div>
          <div className="text-base font-bold text-slate-700 tabular-nums leading-tight">{displayRange}</div>
          <div className="mt-1 h-4 flex items-center justify-end">
            <ChangeIndicator value={minChange} />
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-4 shrink-0">
          <div className="text-center min-w-[64px]">
            <div className="text-[11px] text-slate-400 font-medium mb-1">최저금리</div>
            <div className="text-xl font-bold text-emerald-600 leading-none tabular-nums">
              {minRate !== null ? `${minRate.toFixed(2)}%` : '—'}
            </div>
            <div className="mt-1 h-4 flex items-center justify-center">
              <ChangeIndicator value={minChange} />
            </div>
          </div>

          <div className="w-px h-10 bg-slate-200" />

          <div className="text-center min-w-[64px]">
            <div className="text-[11px] text-slate-400 font-medium mb-1">최고금리</div>
            <div className="text-xl font-bold text-rose-500 leading-none tabular-nums">
              {maxRate !== null ? `${maxRate.toFixed(2)}%` : '—'}
            </div>
            <div className="mt-1 h-4 flex items-center justify-center">
              <ChangeIndicator value={maxChange} />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
