"""
매일 10시 실행: 금리 스크레이핑 → public/rates.json, public/market-rates.json 업데이트
변경사항:
  - 카카오뱅크: '금리정보' 클릭 → '5년 변동 금리 대출' 기준
  - 케이뱅크:  '금리안내' 클릭 → '주기형(금융채 5년)' 기준
  - 삼성생명·삼성화재 스크레이퍼 추가 (매일 업데이트)
  - 시장금리: 전일 영업일 마감 기준 날짜 표시
  - KOFIA 금융채Ⅰ(은행채) 무보증 AAA 시가평가 스크레이핑
"""
import asyncio
import json
import os
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from playwright.async_api import async_playwright

BASE_DIR          = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE       = os.path.join(BASE_DIR, '..', 'public', 'rates.json')
FSS_JSON_FILE     = os.path.join(BASE_DIR, '..', 'public', 'fss.json')
MARKET_RATES_FILE = os.path.join(BASE_DIR, '..', 'public', 'market-rates.json')

# ── 은행 메타 ──────────────────────────────────────────────
BANK_META = {
    '우리은행':   {'id': 'woori',   'colorHex': '#3b82f6', 'name': '우리은행'},
    'KB국민은행': {'id': 'kb',      'colorHex': '#f59e0b', 'name': 'KB국민은행'},
    '하나은행':   {'id': 'hana',    'colorHex': '#14b8a6', 'name': '하나은행'},
    '신한은행':   {'id': 'shinhan', 'colorHex': '#f97316', 'name': '신한은행'},
    'NH농협은행': {'id': 'nh',      'colorHex': '#22c55e', 'name': 'NH농협은행'},
    '카카오뱅크': {'id': 'kakao',   'colorHex': '#fde047', 'name': '카카오뱅크'},
    '케이뱅크':   {'id': 'kbank',   'colorHex': '#a78bfa', 'name': '케이뱅크'},
}
BANK_ORDER = ['kb', 'shinhan', 'hana', 'woori', 'nh', 'kakao', 'kbank']

# ── 보험사 메타 ────────────────────────────────────────────
INS_META = {
    '삼성생명': {'id': 'samsung-life', 'colorHex': '#6366f1', 'name': '삼성생명'},
    '삼성화재': {'id': 'samsung-fire', 'colorHex': '#e11d48', 'name': '삼성화재'},
}
# 한화·교보 – 스크레이퍼 미구현, 이전값 또는 아래 기본값 유지
INS_STATIC_FALLBACK = {
    'hanwha': {'id': 'hanwha', 'name': '한화생명', 'colorHex': '#ef4444',
               'product': '홈드림 모기지론',   'minRate': 4.82, 'maxRate': 6.83, 'minChange': 0, 'maxChange': 0},
    'kyobo':  {'id': 'kyobo',  'name': '교보생명', 'colorHex': '#10b981',
               'product': '교보e아파트론',     'minRate': 5.39, 'maxRate': 5.81, 'minChange': 0, 'maxChange': 0},
}
INS_ORDER = ['samsung-life', 'hanwha', 'kyobo', 'samsung-fire']

BOK_API_KEY = 'Y2VMNWAZOAZNS0806QB9'
BOK_BASE    = 'https://ecos.bok.or.kr/api'


# ── 유틸 ───────────────────────────────────────────────────
def parse_rate(s):
    try:
        return round(float(str(s).replace('%', '').replace(',', '').strip()), 3)
    except Exception:
        return None


def prev_business_day(dt):
    """이전 영업일 반환 (주말만 건너뜀, 공휴일 미처리)"""
    d = dt.date() if hasattr(dt, 'date') else dt
    d = d - timedelta(days=1)
    while d.weekday() >= 5:   # 5=토, 6=일
        d = d - timedelta(days=1)
    return d


# ══════════════════════════════════════════════════════════
#  시중은행 스크레이퍼
# ══════════════════════════════════════════════════════════

async def scrape_woori(browser):
    page = await browser.new_page()
    try:
        await page.goto("https://spot.wooribank.com/pot/Dream?withyou=POLON0070", timeout=30000)
        await page.wait_for_load_state("networkidle", timeout=20000)
        data = await page.evaluate("""() => {
            for (const table of document.querySelectorAll('table')) {
                const cap = table.querySelector('caption');
                if (!cap || !cap.textContent.includes('우리아파트론(일반자금)')) continue;
                for (const row of table.querySelectorAll('tbody tr')) {
                    const c = [...row.querySelectorAll('td')];
                    if (c[0] && c[0].textContent.includes('변동금리(5년)'))
                        return {
                            min_rate: c[3]?.textContent.trim(),
                            max_rate: c[1]?.textContent.trim()
                        };
                }
            }
            return null;
        }""")
        if data:
            return {'bank': '우리은행', 'product': '우리아파트론 변동금리(5년)',
                    'min_rate': data['min_rate'], 'max_rate': data['max_rate'], 'status': 'success'}
        return {'bank': '우리은행', 'status': 'error'}
    except Exception as e:
        return {'bank': '우리은행', 'status': 'error', 'message': str(e)[:100]}
    finally:
        await page.close()


async def scrape_kb(browser):
    page = await browser.new_page()
    try:
        await page.goto(
            "https://obank.kbstar.com/quics?page=C103557&cc=b104363:b104516&isNew=N&prcode=LN20001160&QSL=F",
            timeout=30000)
        await page.wait_for_load_state("networkidle", timeout=20000)
        await page.get_by_role("tab", name="금리 및 이율").click()
        await page.wait_for_timeout(2000)
        data = await page.evaluate("""() => {
            for (const row of document.querySelectorAll('table tbody tr')) {
                const c = [...row.querySelectorAll('td')];
                if (c[0] && c[0].textContent.trim() === '금융채5년')
                    return { min_rate: c[4]?.textContent.trim(), max_rate: c[5]?.textContent.trim() };
            }
            return null;
        }""")
        if data:
            return {'bank': 'KB국민은행', 'product': 'KB주택담보대출 금융채5년',
                    'min_rate': data['min_rate'], 'max_rate': data['max_rate'], 'status': 'success'}
        return {'bank': 'KB국민은행', 'status': 'error'}
    except Exception as e:
        return {'bank': 'KB국민은행', 'status': 'error', 'message': str(e)[:100]}
    finally:
        await page.close()


async def scrape_hana(browser):
    page = await browser.new_page()
    try:
        await page.goto(
            "https://www.kebhana.com/app/portal/mkt/contents/rate_p02_03.do?actionCode=02&subMenu=21&RateIrdCd=072100210001D",
            timeout=30000)
        await page.wait_for_load_state("networkidle", timeout=20000)
        data = await page.evaluate("""() => {
            for (const table of document.querySelectorAll('table')) {
                for (const row of table.querySelectorAll('tbody tr')) {
                    const c = [...row.querySelectorAll('td')];
                    if (c[0] && c[0].textContent.includes('5년물 금융채')) {
                        const range = c[5]?.textContent.trim() || '';
                        const parts = range.split('~');
                        return { min_rate: parts[0]?.trim(), max_rate: parts[1]?.trim() };
                    }
                }
            }
            return null;
        }""")
        if data:
            return {'bank': '하나은행', 'product': '하나 혼합금리 모기지론 5년물 금융채',
                    'min_rate': data['min_rate'], 'max_rate': data['max_rate'], 'status': 'success'}
        return {'bank': '하나은행', 'status': 'error'}
    except Exception as e:
        return {'bank': '하나은행', 'status': 'error', 'message': str(e)[:100]}
    finally:
        await page.close()


async def scrape_shinhan(browser):
    page = await browser.new_page()
    try:
        await page.goto("https://bank.shinhan.com/index.jsp?cr=020305010000&pcd=S614221100", timeout=30000)
        await page.wait_for_selector('[role="tab"]', timeout=10000)
        await page.wait_for_timeout(1000)
        tabs = await page.query_selector_all('[role="tab"]')
        for t in tabs:
            if "금리안내" in await t.inner_text():
                await t.click()
                break
        await page.wait_for_timeout(4000)
        data = await page.evaluate("""() => {
            for (const row of document.querySelectorAll('[role="row"]')) {
                const cells = [...row.querySelectorAll('[role="gridcell"]')];
                if (cells[0] && cells[0].textContent.trim() === '금융채(5년)') {
                    const s = v => (v || '').replace('%', '').trim() || '-';
                    return { min_rate: s(cells[4]?.textContent), max_rate: s(cells[5]?.textContent) };
                }
            }
            return null;
        }""")
        if data:
            return {'bank': '신한은행', 'product': '신한주택대출(아파트) 금융채(5년)',
                    'min_rate': data['min_rate'], 'max_rate': data['max_rate'], 'status': 'success'}
        return {'bank': '신한은행', 'status': 'error'}
    except Exception as e:
        return {'bank': '신한은행', 'status': 'error', 'message': str(e)[:100]}
    finally:
        await page.close()


async def scrape_nh(browser):
    # NH농협은행 금융상품몰 > 대출 > 주택/전세 > NH주택담보대출_5년주기형
    # URL 변경 시: smartmarket.nonghyup.com → 대출 → 주택/전세 탭에서 동일 상품 탐색 (농축협 아님)
    page = await browser.new_page()
    try:
        await page.goto("https://smartmarket.nonghyup.com/servlet/BFLNW0004R.view", timeout=30000)
        await page.wait_for_load_state("networkidle", timeout=20000)
        data = await page.evaluate("""() => {
            for (const row of document.querySelectorAll('table tr')) {
                const c = [...row.querySelectorAll('td')];
                if (!c.find(td => td.textContent.includes('NH주택담보대출_5년주기형'))) continue;
                // c[3] = '최고 연X.XX%최저 연X.XX%' 금리 텍스트 셀
                const text = c[3]?.textContent || '';
                const maxM = text.match(/최고\\s*연\\s*([\\d.]+)/);
                const minM = text.match(/최저\\s*연\\s*([\\d.]+)/);
                return { min_rate: minM?.[1] || '-', max_rate: maxM?.[1] || '-' };
            }
            return null;
        }""")
        if data:
            return {'bank': 'NH농협은행', 'product': 'NH주택담보대출_5년주기형',
                    'min_rate': data['min_rate'], 'max_rate': data['max_rate'], 'status': 'success'}
        return {'bank': 'NH농협은행', 'status': 'error'}
    except Exception as e:
        return {'bank': 'NH농협은행', 'status': 'error', 'message': str(e)[:100]}
    finally:
        await page.close()


# ══════════════════════════════════════════════════════════
#  인터넷은행 스크레이퍼 (개선)
# ══════════════════════════════════════════════════════════

async def scrape_kakao(browser):
    """
    카카오뱅크 - '금리정보' 아코디언 클릭 → '5년 변동금리 대출' 기준
    페이지 구조: .board_item 아코디언, 클릭 시 .board_item.on 클래스 추가
    금리 표시: '5년 변동금리 대출\n연 X.XXX% ~ Y.YY% (기준일)'
    """
    page = await browser.new_page()
    try:
        await page.goto(
            "https://www.kakaobank.com/products/mortgageLoan",
            timeout=30000, wait_until='domcontentloaded'
        )
        await page.wait_for_load_state('networkidle', timeout=20000)
        await page.wait_for_timeout(1000)

        # '금리정보' 링크(a.link_tit) 클릭 - get_by_role로 정확히 타겟팅
        await page.get_by_role('link', name='금리정보').click()
        await page.wait_for_timeout(1500)

        data = await page.evaluate("""() => {
            // '금리정보' 섹션(.board_item.on)에서 데이터 추출
            const boardItems = [...document.querySelectorAll('.board_item.on')];
            const rateItem = boardItems.find(el =>
                el.querySelector('a')?.textContent?.trim() === '금리정보'
            );

            const txt = rateItem ? (rateItem.innerText || '') : (document.body.innerText || '');

            // '5년 변동금리 대출' 다음 줄의 '연 X.XXX% ~ Y.YY%' 패턴
            const m = txt.match(/5년\\s*변동금리\\s*대출[\\s\\S]*?연\\s*([\\d.]+)%\\s*~\\s*([\\d.]+)%/);
            if (m) return { min_rate: m[1], max_rate: m[2] };

            return null;
        }""")

        if data and data.get('min_rate'):
            return {'bank': '카카오뱅크', 'product': '카카오뱅크 주담대 5년 변동',
                    'min_rate': data['min_rate'], 'max_rate': data.get('max_rate', '-'), 'status': 'success'}
        return {'bank': '카카오뱅크', 'status': 'error', 'message': '5년 변동 금리 섹션 없음'}
    except Exception as e:
        return {'bank': '카카오뱅크', 'status': 'error', 'message': str(e)[:100]}
    finally:
        await page.close()


async def scrape_kbank(browser):
    """
    케이뱅크 - 아파트담보대출 페이지에서 '금리안내' Radix UI 아코디언 클릭
    → Shadow DOM에서 주기형금리(금융채 5년) 최저/최고금리 추출
    테이블 컬럼: 기준금리 | 가산금리 | 최저금리 | 최고금리
    (Radix UI accordion: 콘텐츠가 Shadow DOM에 있어 일반 querySelector로 접근 불가)
    """
    page = await browser.new_page()
    try:
        await page.goto(
            "https://www.kbanknow.com/web/product/loan/apt-mortgage",
            timeout=30000, wait_until='networkidle'
        )
        await page.wait_for_timeout(3000)
        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await page.wait_for_timeout(1000)

        # Radix UI 아코디언 버튼 클릭 (data-state 속성으로 Radix 버튼 식별)
        btn = page.locator('button[data-state]:has-text("금리안내")').last
        if await btn.count() == 0:
            btn = page.locator('button:has-text("금리안내")').last
        await btn.scroll_into_view_if_needed()
        await btn.click()
        await page.wait_for_timeout(5000)

        data = await page.evaluate("""() => {
            // Shadow DOM 탐색 - 케이뱅크는 금리 테이블을 Shadow DOM 안에 렌더링
            function findShadowWithJuki(el) {
                if (el.shadowRoot) {
                    const html = el.shadowRoot.innerHTML;
                    if (html.includes("\\uC8FC\\uAE30\\uD615") || html.includes("5\\uB144")) {
                        return el.shadowRoot;
                    }
                }
                for (const child of el.children) {
                    const r = findShadowWithJuki(child);
                    if (r) return r;
                }
                return null;
            }

            const sr = findShadowWithJuki(document.body);
            if (!sr) return null;

            // TreeWalker로 텍스트 노드 수집
            const walker = document.createTreeWalker(sr, NodeFilter.SHOW_TEXT);
            const texts = [];
            let node;
            while ((node = walker.nextNode())) {
                const t = node.textContent.trim();
                if (t) texts.push(t);
            }

            // "주기형" 텍스트 이후에서 숫자% 패턴 추출
            const jukiIdx = texts.findIndex(t => t.includes("\\uC8FC\\uAE30\\uD615"));
            if (jukiIdx < 0) return { error: "주기형 텍스트 없음" };

            const after = texts.slice(jukiIdx, jukiIdx + 30).join(' ');
            const nums = [...after.matchAll(/([0-9]+\\.?[0-9]*)\\s*%/g)].map(m => parseFloat(m[1]));

            // 기준금리, 가산금리min, 가산금리max, 최저금리, 최고금리 순서
            if (nums.length >= 4) {
                return {
                    min_rate: String(nums[nums.length - 2]),
                    max_rate: String(nums[nums.length - 1])
                };
            }
            return { error: "숫자 부족: " + nums.join(','), raw: after.substring(0, 200) };
        }""")

        if data and data.get('min_rate'):
            return {
                'bank': '케이뱅크',
                'product': '케이뱅크 아파트담보대출 주기형(금융채 5년)',
                'min_rate': data['min_rate'],
                'max_rate': data.get('max_rate', '-'),
                'status': 'success'
            }
        err = data.get('error', '알 수 없음') if data else 'Shadow DOM 없음'
        return {'bank': '케이뱅크', 'status': 'error', 'message': err}
    except Exception as e:
        return {'bank': '케이뱅크', 'status': 'error', 'message': str(e)[:100]}
    finally:
        await page.close()


# ══════════════════════════════════════════════════════════
#  보험사 스크레이퍼 (신규)
# ══════════════════════════════════════════════════════════

async def scrape_samsung_life(browser):
    """삼성생명 주택담보대출 금리 - 공시 페이지에서 직접 추출
    페이지에 '연 X.XX ~ Y.YY%' 형태로 금리가 노출됨 (탭 클릭 불필요)
    """
    page = await browser.new_page()
    try:
        await page.goto(
            "https://www.samsunglife.com/individual/products/loan/detail/F34820",
            timeout=30000, wait_until='domcontentloaded'
        )
        await page.wait_for_load_state('networkidle', timeout=20000)
        await page.wait_for_timeout(2000)

        data = await page.evaluate("""() => {
            const body = document.body.innerText || '';

            // '대출금리' 섹션 근처에서 '연 X.XX ~ Y.YY%' 패턴 추출
            const idx = body.indexOf('대출금리');
            if (idx > -1) {
                const section = body.substring(idx, idx + 300);
                const m = section.match(/연\\s*([\\d]+\\.[\\d]{2,3})\\s*%?\\s*~\\s*([\\d]+\\.[\\d]{2,3})\\s*%/);
                if (m) return { min_rate: m[1], max_rate: m[2] };
            }

            // 폴백: 전체 페이지에서 '연 X.XX ~ Y.YY%' 패턴
            const m2 = body.match(/연\\s*([3-9]\\.[\\d]{2,3})\\s*%?\\s*~\\s*([3-9]\\.[\\d]{2,3})\\s*%/);
            if (m2) return { min_rate: m2[1], max_rate: m2[2] };

            return null;
        }""")

        if data and data.get('min_rate'):
            return {'bank': '삼성생명', 'product': '삼성생명 주담대 (5년 주기형)',
                    'min_rate': data['min_rate'], 'max_rate': data.get('max_rate'), 'status': 'success'}
        return {'bank': '삼성생명', 'status': 'error', 'message': '금리 패턴 없음'}
    except Exception as e:
        return {'bank': '삼성생명', 'status': 'error', 'message': str(e)[:100]}
    finally:
        await page.close()


async def scrape_samsung_fire(browser):
    """삼성화재 주택담보대출 금리 - 공시 페이지에서 직접 추출
    URL이 /vh/page/VH.HPLN0023.do 로 리다이렉트됨
    '대출금리' 근처에 'X.X~Y.YY%' 형태로 금리 노출 (버튼 클릭 불필요)
    """
    page = await browser.new_page()
    try:
        await page.goto(
            "https://www.samsungfire.com/loan/P_P04_04_01_066.html",
            timeout=30000, wait_until='domcontentloaded'
        )
        await page.wait_for_load_state('networkidle', timeout=20000)
        await page.wait_for_timeout(2000)

        data = await page.evaluate("""() => {
            const body = document.body.innerText || '';

            // '대출금리' 섹션 근처에서 'X.X~Y.YY%' 패턴 추출
            // ※ 소수점 1자리도 허용 (예: 4.7~6.62%)
            const idx = body.indexOf('대출금리');
            if (idx > -1) {
                const section = body.substring(idx, idx + 200);
                const m = section.match(/([3-9](?:\\.\\d{1,3})?)\\s*~\\s*([3-9]\\.\\d{2,3})\\s*%/);
                if (m) return { min_rate: m[1], max_rate: m[2] };
            }

            // 폴백: 전체 페이지에서 X~Y.YY% 또는 X.X~Y.YY% 패턴
            const m2 = body.match(/([3-9](?:\\.\\d{1,3})?)\\s*~\\s*([3-9]\\.\\d{2,3})\\s*%/);
            if (m2) return { min_rate: m2[1], max_rate: m2[2] };

            return null;
        }""")

        if data and data.get('min_rate'):
            return {'bank': '삼성화재', 'product': '삼성화재 주택담보대출',
                    'min_rate': data['min_rate'], 'max_rate': data.get('max_rate'), 'status': 'success'}
        return {'bank': '삼성화재', 'status': 'error', 'message': '금리 패턴 없음'}
    except Exception as e:
        return {'bank': '삼성화재', 'status': 'error', 'message': str(e)[:100]}
    finally:
        await page.close()


# ══════════════════════════════════════════════════════════
#  시장금리: BOK + KOFIA
# ══════════════════════════════════════════════════════════

async def fetch_kofia_fin_bonds(browser, prev_day):
    """
    KOFIA 채권정보센터 - 금융채Ⅰ(은행채) 무보증 AAA 시가평가수익률
    '평가사 평균(`23.1.9~)' 옵션 선택 → 5개 기관 행을 모두 수집해 평균 계산
      기관: 나이스피앤아이, 한국자산평가, KIS자산평가, 에프앤자산평가, 이지자산평가

    컬럼 매핑: val2=6개월(fin6m), val4=1년(fin1y), val8=3년(fin3y), val10=5년(fin5y)
    """
    import xml.etree.ElementTree as ET

    date_str = prev_day.strftime('%Y%m%d')
    kofia_url = (
        'https://www.kofiabond.or.kr/websquare/websquare.html'
        '?w2xPath=/xml/startest/BISBndSrtPrcDay.xml'
        '&divisionId=MBIS01070010000000'
        '&divisionNm=%EC%9D%BC%EC%9E%90%EB%B3%84'
        '&tabIdx=1&w2xHome=/xml/Com/&w2xDocumentRoot='
    )

    page = await browser.new_page()
    try:
        print(f'    KOFIA 금융채 페이지 로딩 ({date_str})...')
        await page.goto(kofia_url, timeout=60000, wait_until='domcontentloaded')
        await page.wait_for_timeout(10000)

        js_result = await page.evaluate("""(dateStr) => {
            return new Promise((resolve) => {
                if (typeof selectComp === 'undefined' || typeof searchData === 'undefined') {
                    resolve({ error: 'WebSquare not initialized' }); return;
                }
                try {
                    selectComp.setValue('평가사 평균(`23.1.9~)');
                    srchDt.setValue(dateStr);
                } catch(e) {
                    resolve({ error: 'setValue failed: ' + e.message }); return;
                }

                const origCallBack = window.callBack;
                window.callBack = function(svcId, fnId, strResp) {
                    origCallBack(svcId, fnId, strResp);
                    if (fnId === 'selectDay') {
                        try {
                            const node = getInstanceNode('respList');
                            const xml  = WebSquare.xml.serialize(node);
                            window.callBack = origCallBack;
                            resolve({ xml: xml || '' });
                        } catch(e) {
                            window.callBack = origCallBack;
                            resolve({ error: 'serialize error: ' + e.message });
                        }
                    }
                };

                searchData();
                setTimeout(() => { window.callBack = origCallBack; resolve({ timeout: true }); }, 20000);
            });
        }""", date_str)

        if js_result.get('error'):
            print(f'    KOFIA 금융채 JS 오류: {js_result["error"]}')
            return {}
        if js_result.get('timeout'):
            print(f'    KOFIA 금융채 타임아웃: 응답 없음')
            return {}

        xml_str = js_result.get('xml', '')
        if not xml_str:
            print(f'    KOFIA 금융채 XML 응답 비어있음')
            return {}

        # XML 파싱 - 5개 기관 금융채Ⅰ(은행채) 무보증 AAA 행을 모두 수집
        root = ET.fromstring(xml_str)
        collected = {'fin6m': [], 'fin1y': [], 'fin3y': [], 'fin5y': []}

        for dto in root.iter('BISBndSrtPrcDayDTO'):
            cat     = (dto.findtext('largeCategoryMrk') or '').strip()
            type_nm = (dto.findtext('typeNmMrk') or '').strip()
            credit  = (dto.findtext('creditRnkMrk') or '').strip()

            if ('금융채' in cat or '은행채' in cat) and '무보증' in type_nm and credit == 'AAA':
                def _get_val(n, _dto=dto):
                    v = _dto.findtext(f'val{n}')
                    if v:
                        try:
                            f = float(v)
                            return f if f > 0 else None
                        except Exception:
                            pass
                    return None

                v2  = _get_val(2);  v4  = _get_val(4)
                v8  = _get_val(8);  v10 = _get_val(10)
                if v2  is not None: collected['fin6m'].append(v2)
                if v4  is not None: collected['fin1y'].append(v4)
                if v8  is not None: collected['fin3y'].append(v8)
                if v10 is not None: collected['fin5y'].append(v10)

        if not any(collected.values()):
            print(f'    KOFIA 금융채: 무보증 AAA 행 없음 (XML 길이={len(xml_str)})')
            return {}

        def _avg(vals):
            return round(sum(vals) / len(vals), 3) if vals else None

        result = {
            'fin6m':  _avg(collected['fin6m']),
            'fin1y':  _avg(collected['fin1y']),
            'fin3y':  _avg(collected['fin3y']),
            'fin5y':  _avg(collected['fin5y']),
        }
        n = max(len(v) for v in collected.values())
        print(f'    KOFIA 금융채 ({date_str}, {n}기관): 6m={result["fin6m"]} 5y={result["fin5y"]}')
        return result

    except Exception as e:
        print(f'    KOFIA 금융채 실패: {e}')
        return {}
    finally:
        await page.close()


async def fetch_kofia_ktb_rates(browser, prev_day):
    """
    KOFIA 채권정보센터 - 국고채 최종호가수익률 (BISLastAskPrcDay.xml)
    채권금리 > 채권금리 메뉴에서 국고채권(3년)/국고채권(10년) val4 값 추출

    val4 = 최종호가수익률 (장 마감 후 확정, 당일 장중에는 빈값)
    조회일 = 전 영업일 → val4 = 해당일 최종호가수익률
    """
    import xml.etree.ElementTree as ET

    date_str = prev_day.strftime('%Y%m%d')
    kofia_url = (
        'https://www.kofiabond.or.kr/websquare/websquare.html'
        '?w2xPath=/xml/bondint/lastrop/BISLastAskPrcDay.xml'
        '&divisionId=MBIS01010010000000'
        '&divisionNm=%EC%B1%84%EA%B6%8C%EA%B8%88%EB%A6%AC'
        '&tabIdx=1&w2xHome=/xml/Com/&w2xDocumentRoot='
    )

    page = await browser.new_page()
    try:
        print(f'    KOFIA 최종호가수익률 페이지 로딩 ({date_str})...')
        await page.goto(kofia_url, timeout=60000, wait_until='domcontentloaded')
        await page.wait_for_timeout(10000)

        js_result = await page.evaluate("""(dateStr) => {
            return new Promise((resolve) => {
                if (typeof srchDt === 'undefined' || typeof searchData === 'undefined') {
                    resolve({ error: 'WebSquare not initialized' }); return;
                }
                try {
                    srchDt.setValue(dateStr);
                } catch(e) {
                    resolve({ error: 'setValue failed: ' + e.message }); return;
                }

                const origCallBack = window.callBack;
                window.callBack = function(svcId, fnId, strResp) {
                    origCallBack(svcId, fnId, strResp);
                    if (svcId === 'BISLastAskPrcROPSrchSO' && fnId === 'listDay') {
                        try {
                            const node = getInstanceNode('respBondInt/root/message/BISComDspDatListDTO');
                            const xml  = WebSquare.xml.serialize(node);
                            window.callBack = origCallBack;
                            resolve({ xml: xml || '' });
                        } catch(e) {
                            window.callBack = origCallBack;
                            resolve({ error: 'serialize error: ' + e.message });
                        }
                    }
                };

                searchData();
                setTimeout(() => { window.callBack = origCallBack; resolve({ timeout: true }); }, 20000);
            });
        }""", date_str)

        if js_result.get('error'):
            print(f'    KOFIA 최종호가 JS 오류: {js_result["error"]}')
            return {}
        if js_result.get('timeout'):
            print(f'    KOFIA 최종호가 타임아웃')
            return {}

        xml_str = js_result.get('xml', '')
        if not xml_str:
            print(f'    KOFIA 최종호가 XML 응답 비어있음')
            return {}

        root = ET.fromstring('<root>' + xml_str + '</root>')
        result = {}
        for dto in root.iter('BISComDspDatDTO'):
            name = (dto.findtext('val1') or '').strip()
            val4_text = (dto.findtext('val4') or '').strip()
            if not val4_text:
                continue
            try:
                v = float(val4_text)
            except Exception:
                continue
            if v <= 0:
                continue
            if '국고채권(3년)' in name:
                result['ktb3y'] = round(v, 3)
            elif '국고채권(10년)' in name:
                result['ktb10y'] = round(v, 3)

        if result:
            print(f'    KOFIA 최종호가 ({date_str}): 3년={result.get("ktb3y")} / 10년={result.get("ktb10y")}')
        else:
            print(f'    KOFIA 최종호가: 국고채 데이터 없음 (XML 길이={len(xml_str)})')
        return result

    except Exception as e:
        print(f'    KOFIA 최종호가 실패: {e}')
        return {}
    finally:
        await page.close()


def update_market_rates(now, kofia_data: dict, kofia_prev_data: dict):
    """
    BOK(국고채) + KOFIA(금융채 AAA) 데이터로 market-rates.json 업데이트
    변동폭: 전 영업일 값 - 전전 영업일 값 (주말·공휴일 무관)
    """
    prev_day = prev_business_day(now)

    def make_rate(label, new_val, prev_val):
        """new_val: 전 영업일값, prev_val: 전전 영업일값 → 변동폭 = new - prev"""
        change = round(new_val - prev_val, 3) if new_val is not None and prev_val is not None else None
        return {'label': label, 'value': new_val, 'change': change}

    print(f'    국고채 (KOFIA): 3년={kofia_data.get("ktb3y")}% / 10년={kofia_data.get("ktb10y")}%')
    print(f'    금융채 (KOFIA): 6m={kofia_data.get("fin6m")} 1y={kofia_data.get("fin1y")} 3y={kofia_data.get("fin3y")} 5y={kofia_data.get("fin5y")}')

    rates_out = {
        'ktb3y':  make_rate('국고채 3년',   kofia_data.get('ktb3y'),  kofia_prev_data.get('ktb3y')),
        'ktb10y': make_rate('국고채 10년',  kofia_data.get('ktb10y'), kofia_prev_data.get('ktb10y')),
        'fin6m':  make_rate('금융채 6개월', kofia_data.get('fin6m'),  kofia_prev_data.get('fin6m')),
        'fin1y':  make_rate('금융채 1년',   kofia_data.get('fin1y'),  kofia_prev_data.get('fin1y')),
        'fin3y':  make_rate('금융채 3년',   kofia_data.get('fin3y'),  kofia_prev_data.get('fin3y')),
        'fin5y':  make_rate('금융채 5년',   kofia_data.get('fin5y'),  kofia_prev_data.get('fin5y')),
    }

    updated_at = f"{prev_day.strftime('%Y.%m.%d')} 마감 기준"
    result = {'updatedAt': updated_at, 'rates': rates_out}
    with open(MARKET_RATES_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f'  [OK] market-rates.json 업데이트: {updated_at}')


# ══════════════════════════════════════════════════════════
#  상담사 금리 (findsr.kr)
# ══════════════════════════════════════════════════════════

async def scrape_counselor_from_findsr(browser, now):
    """findsr.kr 아파트담보대출 금리표에서 상담사 금리 수집 → counselor.json
    URL 변경 시: findsr.kr → 아파트담보대출 금리표 링크 탐색
    """
    COUNSELOR_FILE = os.path.join(BASE_DIR, '..', 'public', 'counselor.json')
    FINDSR_URL     = 'https://findsr.kr/new1/board_ver3_view_test9.html'

    # rv[id] 마지막 2자리 숫자 → 금리 유형
    # 매매: 03~24, 가계: 27~48 (offset +24)
    SUFFIX_MAP = {
        '03': '3개월', '06': '6개월', '09': '1년',    '15': '3년',
        '18': '5년주기', '21': '5년혼합', '24': '만기고정',
        '27': '3개월', '30': '6개월', '33': '1년',    '39': '3년',
        '42': '5년주기', '45': '5년혼합', '48': '만기고정',
    }
    SELL_SUFFIXES = {'03', '06', '09', '15', '18', '21', '24'}

    BANK_META = {
        '국민은행': {'id': 'kb',      'name': 'KB국민은행',  'colorHex': '#f59e0b'},
        '신한은행': {'id': 'shinhan', 'name': '신한은행',    'colorHex': '#f97316'},
        '하나은행': {'id': 'hana',    'name': '하나은행',    'colorHex': '#14b8a6'},
        '우리은행': {'id': 'woori',   'name': '우리은행',    'colorHex': '#3b82f6'},
        '농협은행': {'id': 'nh',      'name': 'NH농협은행',  'colorHex': '#22c55e'},
        '기업은행': {'id': 'ibk',     'name': 'IBK기업은행', 'colorHex': '#6366f1'},
        'IM뱅크':   {'id': 'im',      'name': 'IM뱅크',      'colorHex': '#8b5cf6'},
        '부산은행': {'id': 'bs',      'name': '부산은행',    'colorHex': '#06b6d4'},
        '경남은행': {'id': 'kn',      'name': '경남은행',    'colorHex': '#0ea5e9'},
        '제일은행': {'id': 'sc',      'name': 'SC제일은행',  'colorHex': '#64748b'},
        '수협은행': {'id': 'sh2',     'name': '수협은행',    'colorHex': '#0284c7'},
        '전북은행': {'id': 'jb',      'name': '전북은행',    'colorHex': '#7c3aed'},
        '광주은행': {'id': 'gj',      'name': '광주은행',    'colorHex': '#db2777'},
    }
    INS_META = {
        '삼성생명': {'id': 'samsung-life', 'name': '삼성생명', 'colorHex': '#3b82f6'},
        '한화생명': {'id': 'hanwha',       'name': '한화생명', 'colorHex': '#ef4444'},
        '교보생명': {'id': 'kyobo',        'name': '교보생명', 'colorHex': '#22c55e'},
        '삼성화재': {'id': 'samsung-fire', 'name': '삼성화재', 'colorHex': '#e11d48'},
        '농협손보': {'id': 'nh-ins',       'name': '농협손보', 'colorHex': '#86efac'},
        'KB손보':   {'id': 'kb-ins',       'name': 'KB손보',   'colorHex': '#fde047'},
        '푸본생명': {'id': 'fubon',        'name': '푸본생명', 'colorHex': '#a78bfa'},
        '현대해상': {'id': 'hyundai',      'name': '현대해상', 'colorHex': '#fb923c'},
        '동양생명': {'id': 'dongyang',     'name': '동양생명', 'colorHex': '#2dd4bf'},
        'ABL생명':  {'id': 'abl',          'name': 'ABL생명',  'colorHex': '#94a3b8'},
        '흥국화재': {'id': 'heungkuk',     'name': '흥국화재', 'colorHex': '#ec4899'},
        '하나생명': {'id': 'hana-life',    'name': '하나생명', 'colorHex': '#0891b2'},
    }

    print("\n상담사 금리 수집 시작 (findsr.kr)...")
    page = await browser.new_page()
    try:
        await page.goto(FINDSR_URL, timeout=30000)
        await page.wait_for_load_state('networkidle', timeout=20000)

        items = await page.evaluate("""() => {
            const SUFFIX_MAP = {
                '03': '3개월', '06': '6개월', '09': '1년',    '15': '3년',
                '18': '5년주기', '21': '5년혼합', '24': '만기고정',
                '27': '3개월', '30': '6개월', '33': '1년',    '39': '3년',
                '42': '5년주기', '45': '5년혼합', '48': '만기고정',
            };
            const TYPE_ORDER = ['3개월','6개월','1년','3년','5년주기','5년혼합','만기고정'];
            const results = [];

            for (const bankEl of document.querySelectorAll('.bank')) {
                const nameEl = bankEl.querySelector('.bk-side');
                if (!nameEl) continue;
                const name = nameEl.textContent.trim();

                const sellRates = {}, leaseRates = {};

                for (const dr of bankEl.querySelectorAll('.dr')) {
                    const lbl = dr.querySelector('.dr-lbl');
                    if (!lbl) continue;
                    const lblText = lbl.textContent.trim();
                    const isSell  = lblText.includes('매매');
                    const isLease = lblText.includes('가계');
                    if (!isSell && !isLease) continue;

                    for (const rv of dr.querySelectorAll('.rv[id]')) {
                        const val = rv.textContent.trim();
                        if (!val) continue;
                        const suffix = rv.id.slice(-2);
                        const type = SUFFIX_MAP[suffix];
                        if (!type) continue;
                        const num = parseFloat(val);
                        if (isNaN(num)) continue;
                        if (isSell) sellRates[type] = num;
                        else         leaseRates[type] = num;
                    }
                }

                const rates = [];
                for (const type of TYPE_ORDER) {
                    if (sellRates[type] != null || leaseRates[type] != null) {
                        rates.push({
                            type,
                            sell:  sellRates[type]  ?? null,
                            lease: leaseRates[type] ?? null,
                        });
                    }
                }
                results.push({ name, rates: rates.length > 0 ? rates : null });
            }
            return results;
        }""")

        banks_out = []
        ins_out   = []
        for item in items:
            name  = item['name']
            rates = item['rates']
            if name in BANK_META:
                m = BANK_META[name]
                banks_out.append({'id': m['id'], 'name': m['name'],
                                  'colorHex': m['colorHex'], 'rates': rates})
            elif name in INS_META:
                m = INS_META[name]
                ins_out.append({'id': m['id'], 'name': m['name'],
                                'colorHex': m['colorHex'], 'rates': rates})

        updated_at = now.strftime('%Y.%m.%d 기준')
        result = {'updatedAt': updated_at, 'banks': banks_out, 'insurances': ins_out}
        with open(COUNSELOR_FILE, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"  [OK] counselor.json 업데이트 완료 ({updated_at}): "
              f"{len(banks_out)}개 은행, {len(ins_out)}개 보험사")

    except Exception as e:
        print(f"  [NG] 상담사 금리 업데이트 실패: {e}")
    finally:
        await page.close()


# ══════════════════════════════════════════════════════════
#  FSS 월별 업데이트
# ══════════════════════════════════════════════════════════

def update_fss_history(now):
    FSS_API_KEY = '736b1d88e7160ca02d43154c35ca6bc6'
    FSS_BASE = 'https://finlife.fss.or.kr/finlifeapi/mortgageLoanProductsSearch.json'

    BANK_MATCH = {
        '국민은행': 'kb', '신한은행': 'shinhan', '하나은행': 'hana',
        '우리은행': 'woori', '농협은행': 'nh',
    }
    INS_MATCH = {
        '삼성생명': 'samsungLife', '한화생명': 'hanwha',
        '교보생명': 'kyobo', '삼성화재': 'samsungFire',
    }

    def fetch_fss(grp):
        url = f'{FSS_BASE}?auth={FSS_API_KEY}&topFinGrpNo={grp}&pageNo=1'
        with urllib.request.urlopen(url, timeout=15) as r:
            return json.loads(r.read().decode('utf-8'))

    def calc_mins(base_list, option_list, match_map):
        result = {}
        for keyword, uid in match_map.items():
            matched_prods = [p for p in base_list if keyword in p.get('kor_co_nm', '')]
            apt_prods  = [p for p in matched_prods if '(아파트)' in p.get('fin_prdt_nm', '')]
            target     = apt_prods if apt_prods else matched_prods
            codes      = {p['fin_prdt_cd'] for p in target}
            opts = [o for o in option_list
                    if o.get('fin_prdt_cd') in codes
                    and o.get('mrtg_type') == 'A'
                    and o.get('rpay_type') == 'D']
            if not opts:
                opts = [o for o in option_list
                        if o.get('fin_prdt_cd') in codes and o.get('mrtg_type') == 'A']
            if not opts:
                opts = [o for o in option_list if o.get('fin_prdt_cd') in codes]
            mins = [o['lend_rate_min'] for o in opts if o.get('lend_rate_min') and o['lend_rate_min'] > 0]
            result[uid] = round(min(mins), 2) if mins else None
        return result

    try:
        b_json    = fetch_fss('020000')
        i_json    = fetch_fss('050000')
        bank_mins = calc_mins(b_json['result']['baseList'], b_json['result']['optionList'], BANK_MATCH)
        ins_mins  = calc_mins(i_json['result']['baseList'], i_json['result']['optionList'], INS_MATCH)

        month_label = f"{str(now.year)[2:]}/{now.month:02d}"
        entry = {'month': month_label}
        for uid in ['kb', 'shinhan', 'hana', 'woori', 'nh']:
            entry[uid] = bank_mins.get(uid)
        for uid in ['samsungLife', 'hanwha', 'kyobo', 'samsungFire']:
            entry[uid] = ins_mins.get(uid)

        history = []
        if os.path.exists(FSS_JSON_FILE):
            with open(FSS_JSON_FILE, encoding='utf-8') as f:
                history = json.load(f).get('history', [])

        if history and history[-1].get('month') == month_label:
            history[-1] = entry
        else:
            history.append(entry)

        with open(FSS_JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump({'history': history}, f, ensure_ascii=False, indent=2)
        print(f"  [OK] fss.json 업데이트 완료: {month_label}")
    except Exception as e:
        print(f"  [NG] FSS 수집 실패: {e}")


def update_fss_rates(now):
    """FSS API 전체 응답을 정적 파일로 캐싱 → FSSView에서 라이브 API 대신 사용"""
    FSS_RATES_FILE = os.path.join(BASE_DIR, '..', 'public', 'fss-rates.json')
    FSS_API_KEY = '736b1d88e7160ca02d43154c35ca6bc6'
    FSS_BASE = 'https://finlife.fss.or.kr/finlifeapi/mortgageLoanProductsSearch.json'

    def fetch_fss(grp):
        url = f'{FSS_BASE}?auth={FSS_API_KEY}&topFinGrpNo={grp}&pageNo=1'
        with urllib.request.urlopen(url, timeout=15) as r:
            return json.loads(r.read().decode('utf-8'))

    try:
        banks_json = fetch_fss('020000')
        ins_json   = fetch_fss('050000')
        out = {
            'updatedAt': now.strftime('%Y.%m.%d'),
            'banks':     banks_json,
            'insurances': ins_json,
        }
        with open(FSS_RATES_FILE, 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f"  [OK] fss-rates.json 업데이트 완료: {out['updatedAt']}")
    except Exception as e:
        print(f"  [NG] fss-rates.json 수집 실패: {e}")


# ══════════════════════════════════════════════════════════
#  메인
# ══════════════════════════════════════════════════════════

async def main(args=None):
    counselor_only = getattr(args, 'counselor_only', False)
    skip_counselor = getattr(args, 'skip_counselor', False)

    # ── 기존 데이터 로드 ──────────────────────────────────
    prev_banks = {}
    prev_insurances = {}
    bank_history = []
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, encoding='utf-8') as f:
                prev = json.load(f)
            for b in prev.get('banks', []):
                prev_banks[b['id']] = b
            for ins in prev.get('insurances', []):
                prev_insurances[ins['id']] = ins
            bank_history = prev.get('bankHistory', [])
        except Exception:
            pass

    KST = timezone(timedelta(hours=9))
    now = datetime.now(KST)
    print("금리 수집 시작...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        bank_scraped = []
        ins_scraped  = []

        if not counselor_only:
            # ── 은행 스크레이핑 ──────────────────────────────
            bank_scrapers = [scrape_woori, scrape_kb, scrape_hana, scrape_shinhan, scrape_nh,
                             scrape_kakao, scrape_kbank]
            for fn in bank_scrapers:
                r = await fn(browser)
                bank_scraped.append(r)
                ok = r.get('status') == 'success'
                detail = r.get('message') or f"{r.get('min_rate')} ~ {r.get('max_rate')}"
                print(f"  [{'OK' if ok else 'NG'}] {r.get('bank')}: {detail}")

            # ── 보험사 스크레이핑 ─────────────────────────────
            ins_scrapers = [scrape_samsung_life, scrape_samsung_fire]
            for fn in ins_scrapers:
                r = await fn(browser)
                ins_scraped.append(r)
                ok = r.get('status') == 'success'
                detail = r.get('message') or f"{r.get('min_rate')} ~ {r.get('max_rate')}"
                print(f"  [{'OK' if ok else 'NG'}] {r.get('bank')}: {detail}")

        # ── 상담사 금리 (findsr.kr, 매일 업데이트) ──
        if not skip_counselor:
            await scrape_counselor_from_findsr(browser, now)
        else:
            print("  상담사 금리 업데이트 생략 (--skip-counselor 플래그)")

        if not counselor_only:
            # ── KOFIA 금융채 AAA + 국고채 최종호가수익률 ────
            print("\n시장금리(KOFIA) 수집 중...")
            _prev_day      = prev_business_day(now)
            _prev_prev_day = prev_business_day(_prev_day)
            fin_data       = await fetch_kofia_fin_bonds(browser, _prev_day)
            fin_prev_data  = await fetch_kofia_fin_bonds(browser, _prev_prev_day)
            ktb_data       = await fetch_kofia_ktb_rates(browser, _prev_day)
            ktb_prev_data  = await fetch_kofia_ktb_rates(browser, _prev_prev_day)
            kofia_data      = {**fin_data, **ktb_data}
            kofia_prev_data = {**fin_prev_data, **ktb_prev_data}

        await browser.close()

    # --counselor-only 모드: counselor.json만 업데이트하고 종료
    if counselor_only:
        print("\n[OK] 상담사 금리 업데이트 완료 (--counselor-only)")
        return

    # ── 은행 데이터 빌드 ──────────────────────────────────
    banks = []
    for raw in bank_scraped:
        if raw.get('status') != 'success':
            continue
        meta = BANK_META.get(raw['bank'])
        if not meta:
            continue
        min_r = parse_rate(raw.get('min_rate'))
        max_r = parse_rate(raw.get('max_rate'))
        prev  = prev_banks.get(meta['id'], {})
        min_change = round(min_r - prev['minRate'], 3) if min_r and prev.get('minRate') else 0
        max_change = round(max_r - prev['maxRate'], 3) if max_r and prev.get('maxRate') else 0
        banks.append({
            'id': meta['id'], 'name': meta['name'], 'colorHex': meta['colorHex'],
            'product':   raw.get('product', '주택담보대출'),
            'minRate':   min_r, 'maxRate': max_r,
            'minChange': min_change, 'maxChange': max_change,
        })
    banks.sort(key=lambda b: BANK_ORDER.index(b['id']) if b['id'] in BANK_ORDER else 99)

    # 스크레이핑 실패 시 이전값 유지 (카카오뱅크·케이뱅크 등 인터넷은행 포함)
    bank_ids_done = {b['id'] for b in banks}
    for bid in BANK_ORDER:
        if bid not in bank_ids_done:
            prev_b = prev_banks.get(bid)
            if prev_b:
                banks.append(prev_b)
                print(f"  [--] {bid}: 스크레이핑 실패, 이전값 유지 ({prev_b.get('minRate')} ~ {prev_b.get('maxRate')})")
                bank_ids_done.add(bid)
    banks.sort(key=lambda b: BANK_ORDER.index(b['id']) if b['id'] in BANK_ORDER else 99)

    # ── 보험사 데이터 빌드 ────────────────────────────────
    ins_ids_done = set()
    insurances   = []

    for raw in ins_scraped:
        if raw.get('status') != 'success':
            continue
        meta = INS_META.get(raw['bank'])
        if not meta:
            continue
        min_r = parse_rate(raw.get('min_rate'))
        max_r = parse_rate(raw.get('max_rate'))
        prev_ins = prev_insurances.get(meta['id'], {})
        min_change = round(min_r - prev_ins['minRate'], 3) if min_r and prev_ins.get('minRate') else 0
        max_change = round(max_r - prev_ins['maxRate'], 3) if max_r and prev_ins.get('maxRate') else 0
        insurances.append({
            'id': meta['id'], 'name': meta['name'], 'colorHex': meta['colorHex'],
            'product':   raw.get('product', '주택담보대출'),
            'minRate':   min_r, 'maxRate': max_r,
            'minChange': min_change, 'maxChange': max_change,
        })
        ins_ids_done.add(meta['id'])

    # 스크레이핑 실패 시 이전값 유지
    for meta in INS_META.values():
        if meta['id'] not in ins_ids_done:
            prev_ins = prev_insurances.get(meta['id'])
            if prev_ins:
                insurances.append(prev_ins)
                print(f"  [--] {meta['name']}: 스크레이핑 실패, 이전값 유지")
            ins_ids_done.add(meta['id'])

    # 한화·교보 정적 폴백 (이전값 우선)
    for uid, fallback in INS_STATIC_FALLBACK.items():
        if uid not in ins_ids_done:
            prev_ins = prev_insurances.get(uid, fallback)
            insurances.append(prev_ins)
            ins_ids_done.add(uid)

    insurances.sort(key=lambda i: INS_ORDER.index(i['id']) if i['id'] in INS_ORDER else 99)

    # ── 히스토리 업데이트 ──────────────────────────────────
    today_key   = f"{now.month}/{now.day}"
    today_entry = {'date': today_key}
    for b in banks:
        bid = b['id']
        today_entry[f'{bid}_min'] = b['minRate']
        today_entry[f'{bid}_max'] = b['maxRate']

    if bank_history and bank_history[-1]['date'] == today_key:
        bank_history[-1] = today_entry
    else:
        bank_history.append(today_entry)

    # ── rates.json 저장 ────────────────────────────────────
    result = {
        'updatedAt':   now.strftime('%Y.%m.%d %H:%M 기준'),
        'banks':       banks,
        'insurances':  insurances,
        'bankHistory': bank_history,
    }
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] public/rates.json 업데이트: {result['updatedAt']}")

    # ── FSS 업데이트 (월별 히스토리 + 일별 캐시) ──────────
    print("\nFSS 금리 수집 시작...")
    update_fss_history(now)
    update_fss_rates(now)

    # ── 시장금리 저장 ──────────────────────────────────────
    print("\n시장금리 저장 중...")
    update_market_rates(now, kofia_data, kofia_prev_data)

    # ── Git commit & push (로컬 실행 시) ─────────────────
    if not os.environ.get('CI'):
        import subprocess
        repo_dir   = os.path.join(BASE_DIR, '..')
        commit_msg = f"chore: update rates {result['updatedAt']}"
        try:
            subprocess.run(['git', 'add',
                            'public/rates.json',      'public/counselor.json',
                            'public/fss.json',         'public/market-rates.json',
                            'public/fss-rates.json'],
                           cwd=repo_dir, check=True)
            subprocess.run(['git', 'commit', '-m', commit_msg], cwd=repo_dir, check=True)
            subprocess.run(['git', 'push', 'origin', 'master'], cwd=repo_dir, check=True)
            print("[OK] GitHub 푸시 완료")
        except subprocess.CalledProcessError as e:
            print(f"[NG] Git 오류: {e}")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--counselor-only', action='store_true',
                        help='findsr.kr 상담사 금리만 수집 (counselor.json 업데이트)')
    parser.add_argument('--skip-counselor', action='store_true',
                        help='상담사 금리 수집 제외 (매일 기본 실행용)')
    _args = parser.parse_args()
    asyncio.run(main(_args))
