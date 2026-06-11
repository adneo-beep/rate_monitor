export default function RateRow({ name, product, minRate, maxRate, colorHex, url }) {
  return (
    <div className="flex items-center py-4 px-5 border-b border-slate-100 last:border-0 hover:bg-slate-50 transition-colors">
      <div className="flex items-center gap-3 flex-1 min-w-0 mr-4">
        <div className="w-1.5 h-10 rounded-full shrink-0" style={{ backgroundColor: colorHex }} />
        <div className="min-w-0">
          {url ? (
            <a href={url} target="_blank" rel="noopener noreferrer"
               className="font-semibold text-sm leading-tight text-slate-800 hover:text-blue-600 hover:underline underline-offset-2 transition-colors">
              {name} <span className="text-[10px] text-slate-400 font-normal">↗</span>
            </a>
          ) : (
            <div className="font-semibold text-slate-800 text-sm leading-tight">{name}</div>
          )}
          <div className="text-xs text-slate-400 truncate mt-0.5">{product}</div>
        </div>
      </div>

      <div className="flex items-center gap-4 shrink-0">
        <div className="text-center min-w-[64px]">
          <div className="text-[11px] text-slate-400 font-medium mb-1">최저금리</div>
          <div className="text-xl font-bold text-emerald-600 leading-none tabular-nums">
            {minRate !== null ? `${minRate.toFixed(2)}%` : '—'}
          </div>
        </div>

        <div className="w-px h-10 bg-slate-200" />

        <div className="text-center min-w-[64px]">
          <div className="text-[11px] text-slate-400 font-medium mb-1">최고금리</div>
          <div className="text-xl font-bold text-rose-500 leading-none tabular-nums">
            {maxRate !== null ? `${maxRate.toFixed(2)}%` : '—'}
          </div>
        </div>
      </div>
    </div>
  )
}
