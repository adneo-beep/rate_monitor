// ─── 금융사 홈페이지 공시 기준 ───────────────────────────────────────────────
export const MOCK_BANK_RATES = {
  updatedAt: '2026.05.28 17:03 기준',
  banks: [
    { id: 'kb',      name: 'KB국민은행', colorHex: '#f59e0b', product: 'KB주택담보대출 금융채5년',               minRate: 5.07,  maxRate: 6.47,  minChange: -0.05,  maxChange:  0    },
    { id: 'shinhan', name: '신한은행',   colorHex: '#f97316', product: '신한주택대출(아파트) 금융채(5년)',       minRate: 4.63,  maxRate: 6.04,  minChange: -0.01,  maxChange: -0.01 },
    { id: 'hana',    name: '하나은행',   colorHex: '#14b8a6', product: '하나 혼합금리 모기지론 5년물 금융채',    minRate: 5.636, maxRate: 6.936, minChange: +0.056, maxChange: +0.056 },
    { id: 'woori',   name: '우리은행',   colorHex: '#3b82f6', product: '우리아파트론 변동금리(5년)',              minRate: 4.25,  maxRate: 6.64,  minChange: -0.01,  maxChange: null   },
    { id: 'nh',      name: 'NH농협은행', colorHex: '#22c55e', product: 'NH주택담보대출_5년주기형',               minRate: 4.51,  maxRate: 7.11,  minChange: -0.02,  maxChange: -0.02  },
    { id: 'kakao',   name: '카카오뱅크', colorHex: '#fde047', product: '카카오뱅크 주택담보대출',                 minRate: 3.89,  maxRate: 6.29,  minChange: 0,      maxChange: 0      },
    { id: 'kbank',   name: '케이뱅크',   colorHex: '#a78bfa', product: '케이뱅크 아파트담보대출',                 minRate: 3.95,  maxRate: 6.15,  minChange: 0,      maxChange: 0      },
  ],
  insurances: [
    // Samsung Life: displayRange로 웹사이트 표기 방식 그대로 노출
    { id: 'samsung-life',  name: '삼성생명', colorHex: '#6366f1', product: '삼성생명주택담보대출',        minRate: 4.54, maxRate: 6.34, minChange: 0, maxChange: 0 },
    { id: 'hanwha',        name: '한화생명', colorHex: '#ef4444', product: '홈드림 모기지론',             minRate: 4.82, maxRate: 6.83, minChange: 0, maxChange: 0 },
    { id: 'kyobo',         name: '교보생명', colorHex: '#10b981', product: '교보e아파트론',               minRate: 5.39, maxRate: 5.81, minChange: 0, maxChange: 0 },
    { id: 'samsung-fire',  name: '삼성화재', colorHex: '#e11d48', product: '삼성화재 주택담보대출',       minRate: 4.65, maxRate: 6.78, minChange: 0, maxChange: 0 },
  ],
}

// ─── 금융감독원 공시 기준 (Mock) ──────────────────────────────────────────────
export const MOCK_FSS_RATES = {
  updatedAt: '2026년 5월 기준',
  banks: [
    { id: 'kb',      name: 'KB국민은행', colorHex: '#f59e0b', product: '주택담보대출(혼합형)', minRate: 4.89, maxRate: 6.31, minChange: -0.12, maxChange: -0.08 },
    { id: 'shinhan', name: '신한은행',   colorHex: '#f97316', product: '주택담보대출(혼합형)', minRate: 4.52, maxRate: 5.97, minChange: -0.08, maxChange: -0.05 },
    { id: 'hana',    name: '하나은행',   colorHex: '#14b8a6', product: '주택담보대출(혼합형)', minRate: 5.21, maxRate: 6.67, minChange: +0.05, maxChange: +0.03 },
    { id: 'woori',   name: '우리은행',   colorHex: '#3b82f6', product: '주택담보대출(혼합형)', minRate: 4.35, maxRate: 5.82, minChange:  0,    maxChange: +0.02 },
    { id: 'nh',      name: 'NH농협은행', colorHex: '#22c55e', product: '주택담보대출(혼합형)', minRate: 4.48, maxRate: 6.95, minChange: -0.03, maxChange: -0.01 },
  ],
  insurances: [
    { id: 'samsung-life',  name: '삼성생명', colorHex: '#6366f1', product: '주택담보대출', displayRange: '연 3.45% ~ 6.38%', minRate: 3.45, maxRate: 6.38, minChange: -0.08, maxChange: -0.07 },
    { id: 'hanwha',        name: '한화생명', colorHex: '#ef4444', product: '주택담보대출', minRate: 4.75, maxRate: 6.75, minChange: -0.07, maxChange: -0.08 },
    { id: 'kyobo',         name: '교보생명', colorHex: '#10b981', product: '주택담보대출', minRate: 5.32, maxRate: 5.78, minChange: -0.07, maxChange: -0.03 },
    { id: 'samsung-fire',  name: '삼성화재', colorHex: '#e11d48', product: '주택담보대출', minRate: 4.58, maxRate: 6.71, minChange: -0.07, maxChange: -0.07 },
  ],
}

// ─── 일별 시계열 차트 데이터 (5월 전체, 5/28 실측값 기준) ─────────────────────
export const BANK_CHART_DATA = [
  { date: '5/1',  kb: 5.21, shinhan: 4.75, hana: 5.78,  woori: 4.36, nh: 4.63 },
  { date: '5/2',  kb: 5.20, shinhan: 4.74, hana: 5.77,  woori: 4.35, nh: 4.62 },
  { date: '5/3',  kb: 5.20, shinhan: 4.74, hana: 5.77,  woori: 4.35, nh: 4.62 },
  { date: '5/4',  kb: 5.19, shinhan: 4.73, hana: 5.76,  woori: 4.35, nh: 4.61 },
  { date: '5/5',  kb: 5.19, shinhan: 4.73, hana: 5.76,  woori: 4.34, nh: 4.61 },
  { date: '5/6',  kb: 5.18, shinhan: 4.72, hana: 5.75,  woori: 4.34, nh: 4.60 },
  { date: '5/7',  kb: 5.18, shinhan: 4.72, hana: 5.75,  woori: 4.33, nh: 4.60 },
  { date: '5/8',  kb: 5.17, shinhan: 4.71, hana: 5.74,  woori: 4.33, nh: 4.59 },
  { date: '5/9',  kb: 5.17, shinhan: 4.71, hana: 5.74,  woori: 4.32, nh: 4.59 },
  { date: '5/10', kb: 5.16, shinhan: 4.70, hana: 5.73,  woori: 4.32, nh: 4.58 },
  { date: '5/11', kb: 5.15, shinhan: 4.70, hana: 5.73,  woori: 4.31, nh: 4.58 },
  { date: '5/12', kb: 5.15, shinhan: 4.69, hana: 5.72,  woori: 4.31, nh: 4.57 },
  { date: '5/13', kb: 5.14, shinhan: 4.69, hana: 5.72,  woori: 4.31, nh: 4.57 },
  { date: '5/14', kb: 5.14, shinhan: 4.68, hana: 5.71,  woori: 4.30, nh: 4.57 },
  { date: '5/15', kb: 5.13, shinhan: 4.68, hana: 5.71,  woori: 4.30, nh: 4.56 },
  { date: '5/16', kb: 5.12, shinhan: 4.67, hana: 5.70,  woori: 4.30, nh: 4.55 },
  { date: '5/17', kb: 5.12, shinhan: 4.67, hana: 5.70,  woori: 4.29, nh: 4.55 },
  { date: '5/18', kb: 5.11, shinhan: 4.66, hana: 5.69,  woori: 4.29, nh: 4.55 },
  { date: '5/19', kb: 5.11, shinhan: 4.66, hana: 5.69,  woori: 4.28, nh: 4.54 },
  { date: '5/20', kb: 5.10, shinhan: 4.65, hana: 5.68,  woori: 4.28, nh: 4.54 },
  { date: '5/21', kb: 5.10, shinhan: 4.65, hana: 5.68,  woori: 4.28, nh: 4.53 },
  { date: '5/22', kb: 5.09, shinhan: 4.65, hana: 5.67,  woori: 4.27, nh: 4.53 },
  { date: '5/23', kb: 5.09, shinhan: 4.64, hana: 5.67,  woori: 4.27, nh: 4.52 },
  { date: '5/24', kb: 5.08, shinhan: 4.64, hana: 5.66,  woori: 4.26, nh: 4.52 },
  { date: '5/25', kb: 5.08, shinhan: 4.64, hana: 5.66,  woori: 4.26, nh: 4.52 },
  { date: '5/26', kb: 5.08, shinhan: 4.63, hana: 5.65,  woori: 4.26, nh: 4.52 },
  { date: '5/27', kb: 5.07, shinhan: 4.63, hana: 5.64,  woori: 4.25, nh: 4.51 },
  { date: '5/28', kb: 5.07, shinhan: 4.63, hana: 5.636, woori: 4.25, nh: 4.51 },
]

export const INSURANCE_CHART_DATA = [
  { date: '5/1',  samsungLife: 4.68, hanwha: 4.96, kyobo: 5.53, samsungFire: 4.79 },
  { date: '5/2',  samsungLife: 4.68, hanwha: 4.95, kyobo: 5.52, samsungFire: 4.78 },
  { date: '5/3',  samsungLife: 4.67, hanwha: 4.95, kyobo: 5.52, samsungFire: 4.78 },
  { date: '5/4',  samsungLife: 4.67, hanwha: 4.94, kyobo: 5.51, samsungFire: 4.77 },
  { date: '5/5',  samsungLife: 4.66, hanwha: 4.94, kyobo: 5.51, samsungFire: 4.77 },
  { date: '5/6',  samsungLife: 4.66, hanwha: 4.93, kyobo: 5.50, samsungFire: 4.76 },
  { date: '5/7',  samsungLife: 4.65, hanwha: 4.93, kyobo: 5.50, samsungFire: 4.76 },
  { date: '5/8',  samsungLife: 4.65, hanwha: 4.92, kyobo: 5.49, samsungFire: 4.75 },
  { date: '5/9',  samsungLife: 4.64, hanwha: 4.92, kyobo: 5.49, samsungFire: 4.75 },
  { date: '5/10', samsungLife: 4.64, hanwha: 4.91, kyobo: 5.48, samsungFire: 4.74 },
  { date: '5/11', samsungLife: 4.63, hanwha: 4.91, kyobo: 5.47, samsungFire: 4.74 },
  { date: '5/12', samsungLife: 4.63, hanwha: 4.90, kyobo: 5.47, samsungFire: 4.73 },
  { date: '5/13', samsungLife: 4.62, hanwha: 4.90, kyobo: 5.46, samsungFire: 4.73 },
  { date: '5/14', samsungLife: 4.62, hanwha: 4.89, kyobo: 5.46, samsungFire: 4.72 },
  { date: '5/15', samsungLife: 4.62, hanwha: 4.89, kyobo: 5.45, samsungFire: 4.72 },
  { date: '5/16', samsungLife: 4.61, hanwha: 4.88, kyobo: 5.45, samsungFire: 4.71 },
  { date: '5/17', samsungLife: 4.61, hanwha: 4.88, kyobo: 5.44, samsungFire: 4.71 },
  { date: '5/18', samsungLife: 4.60, hanwha: 4.87, kyobo: 5.44, samsungFire: 4.70 },
  { date: '5/19', samsungLife: 4.60, hanwha: 4.87, kyobo: 5.43, samsungFire: 4.70 },
  { date: '5/20', samsungLife: 4.59, hanwha: 4.86, kyobo: 5.43, samsungFire: 4.69 },
  { date: '5/21', samsungLife: 4.59, hanwha: 4.86, kyobo: 5.42, samsungFire: 4.69 },
  { date: '5/22', samsungLife: 4.58, hanwha: 4.85, kyobo: 5.42, samsungFire: 4.68 },
  { date: '5/23', samsungLife: 4.58, hanwha: 4.85, kyobo: 5.41, samsungFire: 4.68 },
  { date: '5/24', samsungLife: 4.57, hanwha: 4.84, kyobo: 5.41, samsungFire: 4.67 },
  { date: '5/25', samsungLife: 4.57, hanwha: 4.84, kyobo: 5.41, samsungFire: 4.67 },
  { date: '5/26', samsungLife: 4.56, hanwha: 4.83, kyobo: 5.40, samsungFire: 4.66 },
  { date: '5/27', samsungLife: 4.55, hanwha: 4.83, kyobo: 5.40, samsungFire: 4.66 },
  { date: '5/28', samsungLife: 4.54, hanwha: 4.82, kyobo: 5.39, samsungFire: 4.65 },
]

// ─── 우리동네 대출상담사 기준 ─────────────────────────────────────────────────
export const COUNSELOR_SOURCE_URL = 'https://findsr.kr/new1/product.html'

// findsr.kr 2026.05.28 실측값
export const COUNSELOR_TABLE_DATA = {
  updatedAt: '2026.05.28 기준',
  banks: [
    {
      id: 'kb', name: 'KB국민은행', colorHex: '#f59e0b',
      rates: [
        { type: '1년',  sell: 4.52, lease: 4.68 },
        { type: '5년',  sell: 5.01, lease: 5.07 },
      ],
    },
    {
      id: 'shinhan', name: '신한은행', colorHex: '#f97316',
      rates: [
        { type: '6개월', sell: 4.37, lease: 4.45 },
        { type: '5년',   sell: 5.14, lease: 5.38 },
      ],
    },
    {
      id: 'hana', name: '하나은행', colorHex: '#14b8a6',
      rates: [
        { type: '6개월',  sell: 4.32, lease: 4.27 },
        { type: '5년주기', sell: 5.35, lease: 5.30 },
        { type: '5년혼합', sell: 5.06, lease: 5.01 },
      ],
    },
    {
      id: 'woori', name: '우리은행', colorHex: '#3b82f6',
      rates: [
        { type: '6개월',  sell: 4.05, lease: 4.12 },
        { type: '5년변동', sell: 4.86, lease: 4.94 },
      ],
    },
    {
      id: 'nh', name: 'NH농협은행', colorHex: '#22c55e',
      rates: [
        { type: '6개월',  sell: 4.32, lease: 4.40 },
        { type: '5년변동', sell: 5.50, lease: 5.58 },
      ],
    },
  ],
  insurances: [
    {
      id: 'samsung-life', name: '삼성생명', colorHex: '#6366f1',
      rates: null,
    },
    {
      id: 'hanwha', name: '한화생명', colorHex: '#ef4444',
      rates: [
        { type: '1년', sell: 5.28, lease: 5.08 },
        { type: '3년', sell: 5.28, lease: 5.08 },
        { type: '5년', sell: 5.02, lease: 4.82 },
      ],
    },
    {
      id: 'kyobo', name: '교보생명', colorHex: '#10b981',
      rates: null,
    },
    {
      id: 'samsung-fire', name: '삼성화재', colorHex: '#e11d48',
      rates: [
        { type: '5년', sell: 4.98, lease: 5.08 },
      ],
    },
  ],
}
