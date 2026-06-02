// BOK API로 국고채 최신 데이터를 market-rates.json에 초기화
import { readFileSync, writeFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dir = dirname(fileURLToPath(import.meta.url));
const OUTPUT = join(__dir, '..', 'public', 'market-rates.json');

const KEY  = 'Y2VMNWAZOAZNS0806QB9';
const BASE = 'https://ecos.bok.or.kr/api';

const today    = new Date().toISOString().slice(0,10).replace(/-/g,'');
const weekAgo  = new Date(Date.now()-7*86400000).toISOString().slice(0,10).replace(/-/g,'');

async function fetchBOK(code) {
  const url = `${BASE}/StatisticSearch/${KEY}/json/kr/1/10/817Y002/D/${weekAgo}/${today}/${code}`;
  const r = await fetch(url);
  const j = await r.json();
  const rows = (j.StatisticSearch?.row ?? []).filter(x => x.DATA_VALUE && x.DATA_VALUE !== '-');
  return rows.length > 0 ? parseFloat(rows[rows.length-1].DATA_VALUE) : null;
}

const [ktb3y, ktb10y] = await Promise.all([
  fetchBOK('010200000'),
  fetchBOK('010210000'),
]);

const now = new Date();
const updatedAt = `${now.getFullYear()}.${String(now.getMonth()+1).padStart(2,'0')}.${String(now.getDate()).padStart(2,'0')} 기준`;

const data = {
  updatedAt,
  rates: {
    ktb3y:  { label: '국고채 3년',   value: ktb3y,  change: null },
    ktb10y: { label: '국고채 10년',  value: ktb10y, change: null },
    fin6m:  { label: '금융채 6개월', value: null, change: null },
    fin1y:  { label: '금융채 1년',   value: null, change: null },
    fin3y:  { label: '금융채 3년',   value: null, change: null },
    fin5y:  { label: '금융채 5년',   value: null, change: null },
  }
};

writeFileSync(OUTPUT, JSON.stringify(data, null, 2), 'utf-8');
console.log(`✅ market-rates.json 초기화 완료`);
console.log(`   국고채 3년:  ${ktb3y}%`);
console.log(`   국고채 10년: ${ktb10y}%`);
