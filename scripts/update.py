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
from datetime import datetime, timedelta
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
    page = await browser.new_page()
    try:
        await page.goto("https://smartmarket.nonghyup.com/servlet/BFLNW0004R.view", timeout=30000)
        await page.wait_for_load_state("networkidle", timeout=20000)
        data = await page.evaluate("""() => {
            for (const row of document.querySelectorAll('table tr')) {
                const c = [...row.querySelectorAll('td')];
                if (!c.find(td => td.textContent.includes('NH주택담보대출_5년주기형'))) continue;
                const text = (c[3] || c[c.length - 2])?.textContent || '';
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
    케이뱅크 - 아파트담보대출 페이지에서 '금리안내' 아코디언 클릭
    → 대출금리 테이블의 '주기형 금리(금융채 5년)' 행에서 최저/최고금리 추출
    테이블 컬럼: 기준금리 | 가산금리 | 최저금리 | 최고금리
    """
    page = await browser.new_page()
    try:
        await page.goto(
            "https://www.kbanknow.com/ib20/mnu/FPMLON250000?phashid=sAySEh8",
            timeout=30000, wait_until='domcontentloaded'
        )
        await page.wait_for_load_state('networkidle', timeout=20000)
        await page.wait_for_timeout(1000)

        # '금리안내' 아코디언 클릭 (a.section-link.ui-accordion-btn)
        await page.locator('a.section-link.ui-accordion-btn:has-text("금리안내")').click()
        await page.wait_for_timeout(2000)

        data = await page.evaluate("""() => {
            // 대출금리 테이블에서 '주기형 금리(금융채 5년)' 행 탐색
            // 컬럼 순서: 기준금리 | 가산금리 | 최저금리 | 최고금리
            for (const tbl of document.querySelectorAll('table')) {
                const tblTxt = tbl.innerText || '';
                if (!tblTxt.includes('주기형') || !tblTxt.includes('최저금리')) continue;

                for (const row of tbl.querySelectorAll('tr')) {
                    const cells = [...row.querySelectorAll('th, td')];
                    const rowTxt = cells[0]?.innerText || '';
                    if (rowTxt.includes('주기형') && (rowTxt.includes('금융채') || rowTxt.includes('5년'))) {
                        const minRate = cells[2]?.innerText.trim().replace('%', '').trim();
                        const maxRate = cells[3]?.innerText.trim().replace('%', '').trim();
                        if (minRate && maxRate) return { min_rate: minRate, max_rate: maxRate };
                    }
                }
            }
            return null;
        }""")

        if data and data.get('min_rate'):
            return {'bank': '케이뱅크', 'product': '케이뱅크 아파트담보대출 주기형(금융채 5년)',
                    'min_rate': data['min_rate'], 'max_rate': data.get('max_rate', '-'), 'status': 'success'}
        return {'bank': '케이뱅크', 'status': 'error', 'message': '주기형 금리 테이블 없음'}
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
        print(f'    KOFIA WebSquare 페이지 로딩 ({date_str})...')
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
            print(f'    KOFIA JS 오류: {js_result["error"]}')
            return {}
        if js_result.get('timeout'):
            print(f'    KOFIA 타임아웃: 응답 없음')
            return {}

        xml_str = js_result.get('xml', '')
        if not xml_str:
            print(f'    KOFIA XML 응답 비어있음')
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
            print(f'    KOFIA: 금융채Ⅰ 무보증 AAA 행 없음 (XML 길이={len(xml_str)})')
            return {}

        # 5개 기관 평균 계산
        def _avg(vals):
            return round(sum(vals) / len(vals), 3) if vals else None

        result = {
            'fin6m': _avg(collected['fin6m']),
            'fin1y': _avg(collected['fin1y']),
            'fin3y': _avg(collected['fin3y']),
            'fin5y': _avg(collected['fin5y']),
        }
        n = max(len(v) for v in collected.values())
        print(f'    KOFIA 금융채Ⅰ AAA 5기관 평균 ({date_str}, {n}개 기관): {result}')
        return result

    except Exception as e:
        print(f'    KOFIA 실패: {e}')
        return {}
    finally:
        await page.close()


def update_market_rates(now, kofia_data: dict):
    """
    BOK(국고채) + KOFIA(금융채 AAA) 데이터로 market-rates.json 업데이트
    기준: 전일 영업일 마감
    """
    prev_day = prev_business_day(now)

    def fetch_bok_rate(item_code):
        """BOK ECOS API - 전일 기준 최신값, 최대 2회 재시도"""
        end_d   = prev_day.strftime('%Y%m%d')
        start_d = (prev_day - timedelta(days=14)).strftime('%Y%m%d')
        url = (f'{BOK_BASE}/StatisticSearch/{BOK_API_KEY}/json/kr/1/10'
               f'/817Y002/D/{start_d}/{end_d}/{item_code}')
        for attempt in range(2):
            try:
                with urllib.request.urlopen(url, timeout=30) as r:
                    j = json.loads(r.read().decode('utf-8'))
                rows = [x for x in (j.get('StatisticSearch', {}).get('row') or [])
                        if x.get('DATA_VALUE') and x['DATA_VALUE'] != '-']
                if rows:
                    return round(float(rows[-1]['DATA_VALUE']), 3)
            except Exception as e:
                print(f'    BOK fetch error ({item_code}) attempt {attempt+1}: {e}')
        return None

    # 이전 값 읽기 (변동폭 계산)
    prev_rates = {}
    if os.path.exists(MARKET_RATES_FILE):
        try:
            with open(MARKET_RATES_FILE, encoding='utf-8') as f:
                prev_rates = json.load(f).get('rates', {})
        except Exception:
            pass

    def make_rate(key, new_val, label):
        old_val = (prev_rates.get(key) or {}).get('value')
        # 새 값이 없으면 이전 값 유지 (스크레이핑 실패 시 데이터 보존)
        val    = new_val if new_val is not None else old_val
        change = round(new_val - old_val, 3) if new_val is not None and old_val is not None else None
        return {'label': label, 'value': val, 'change': change}

    print('  BOK 국고채 조회 중...')
    ktb3y  = fetch_bok_rate('010200000')
    ktb10y = fetch_bok_rate('010210000')
    print(f'    국고채 3년: {ktb3y}%  |  10년: {ktb10y}%')
    print(f'    금융채 (KOFIA): {kofia_data}')

    rates_out = {
        'ktb3y':  make_rate('ktb3y',  ktb3y,               '국고채 3년'),
        'ktb10y': make_rate('ktb10y', ktb10y,              '국고채 10년'),
        'fin6m':  make_rate('fin6m',  kofia_data.get('fin6m'), '금융채 6개월'),
        'fin1y':  make_rate('fin1y',  kofia_data.get('fin1y'), '금융채 1년'),
        'fin3y':  make_rate('fin3y',  kofia_data.get('fin3y'), '금융채 3년'),
        'fin5y':  make_rate('fin5y',  kofia_data.get('fin5y'), '금융채 5년'),
    }

    # 전일 영업일 마감 기준으로 날짜 표시
    updated_at = f"{prev_day.strftime('%Y.%m.%d')} 마감 기준"

    result = {'updatedAt': updated_at, 'rates': rates_out}
    with open(MARKET_RATES_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f'  [OK] market-rates.json 업데이트: {updated_at}')


# ══════════════════════════════════════════════════════════
#  상담사 금리 (Lovable)
# ══════════════════════════════════════════════════════════

async def scrape_counselor_from_lovable(browser, now):
    """loan-rate-scoop.lovable.app에서 금리표 파싱 → counselor.json"""
    COUNSELOR_FILE = os.path.join(BASE_DIR, '..', 'public', 'counselor.json')
    LOVABLE_URL    = 'https://loan-rate-scoop.lovable.app/'

    _BANK_META = {
        '국민':     {'id': 'kb',      'name': 'KB국민은행', 'colorHex': '#f59e0b'},
        '신한':     {'id': 'shinhan', 'name': '신한은행',   'colorHex': '#f97316'},
        '하나':     {'id': 'hana',    'name': '하나은행',   'colorHex': '#14b8a6'},
        '우리':     {'id': 'woori',   'name': '우리은행',   'colorHex': '#3b82f6'},
        '농협은행': {'id': 'nh',      'name': 'NH농협은행', 'colorHex': '#22c55e'},
    }
    _INS_META = {
        '한화생명': {'id': 'hanwha',       'name': '한화생명', 'colorHex': '#ef4444'},
        '삼성화재': {'id': 'samsung-fire', 'name': '삼성화재', 'colorHex': '#e11d48'},
    }
    COL_NORMALIZE = {'5년년': '5년변동', '5년(혼합)': '5년혼합', '5년(주기)': '5년주기'}
    _BANK_ORDER = ['kb', 'shinhan', 'hana', 'woori', 'nh']

    print("\n상담사 금리 수집 시작 (loan-rate-scoop.lovable.app)...")
    try:
        page = await browser.new_page()
        await page.goto(LOVABLE_URL, timeout=30000)
        try:
            await page.wait_for_selector('table tbody tr', timeout=40000)
        except Exception:
            print("  [NG] 테이블 로드 타임아웃")
            await page.close()
            return

        raw = await page.evaluate("""() => {
            const headers = [...document.querySelectorAll('table thead th')]
                .map(h => h.innerText.trim());
            const rows = [...document.querySelectorAll('table tbody tr')].map(r =>
                [...r.querySelectorAll('td, th')].map(c => c.innerText.trim())
            );
            const dateMatch = document.body.innerText.match(/기준일\\s*([\\d-]+)/);
            return { headers, rows, date: dateMatch ? dateMatch[1] : '' };
        }""")
        await page.close()

        headers = raw['headers']
        rows    = raw['rows']
        date_str = raw['date']
        rate_cols = [COL_NORMALIZE.get(h, h) for h in headers[2:]]

        def _parse_rate(s):
            import math
            s = s.strip().replace('%', '')
            try:
                v = round(float(s), 3)
                return None if math.isnan(v) or math.isinf(v) else v
            except Exception:
                return None

        institution_data = {}
        current_bank = None
        for row in rows:
            if not row:
                continue
            if row[0] not in ('생활안정',) and len(row) > 1 and row[1] == '매매':
                current_bank = row[0]
                institution_data[current_bank] = {'sell': row[2:], 'lease': []}
            elif row[0] == '생활안정' and current_bank:
                institution_data[current_bank]['lease'] = row[1:]

        def build_rates(sell_vals, lease_vals):
            rates = []
            for i, col_name in enumerate(rate_cols):
                s = _parse_rate(sell_vals[i]) if i < len(sell_vals) else None
                l = _parse_rate(lease_vals[i]) if i < len(lease_vals) else None
                if s is not None or l is not None:
                    rates.append({'type': col_name, 'sell': s, 'lease': l})
            return rates or None

        banks_out = []
        for key, meta in _BANK_META.items():
            d = institution_data.get(key, {})
            rates = build_rates(d.get('sell', []), d.get('lease', []))
            banks_out.append({'id': meta['id'], 'name': meta['name'],
                              'colorHex': meta['colorHex'], 'rates': rates})
        banks_out.sort(key=lambda b: _BANK_ORDER.index(b['id']) if b['id'] in _BANK_ORDER else 99)

        ins_out = []
        for key, meta in _INS_META.items():
            d = institution_data.get(key, {})
            rates = build_rates(d.get('sell', []), d.get('lease', []))
            ins_out.append({'id': meta['id'], 'name': meta['name'],
                            'colorHex': meta['colorHex'], 'rates': rates})

        if os.path.exists(COUNSELOR_FILE):
            with open(COUNSELOR_FILE, encoding='utf-8') as f:
                prev = json.load(f)
            existing_ids = {i['id'] for i in ins_out}
            for ins in prev.get('insurances', []):
                if ins['id'] not in existing_ids:
                    ins_out.append(ins)

        updated_at = now.strftime('%Y.%m.%d 기준')
        counselor_result = {'updatedAt': updated_at, 'banks': banks_out, 'insurances': ins_out}
        with open(COUNSELOR_FILE, 'w', encoding='utf-8') as f:
            json.dump(counselor_result, f, ensure_ascii=False, indent=2)
        print(f"  [OK] counselor.json 업데이트 완료: {updated_at}")

    except Exception as e:
        print(f"  [NG] 상담사 금리 업데이트 실패: {e}")


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


# ══════════════════════════════════════════════════════════
#  메인
# ══════════════════════════════════════════════════════════

async def main():
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

    now = datetime.now()
    print("금리 수집 시작...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # ── 은행 스크레이핑 ──────────────────────────────
        bank_scrapers = [scrape_woori, scrape_kb, scrape_hana, scrape_shinhan, scrape_nh,
                         scrape_kakao, scrape_kbank]
        bank_scraped = []
        for fn in bank_scrapers:
            r = await fn(browser)
            bank_scraped.append(r)
            ok = r.get('status') == 'success'
            detail = r.get('message') or f"{r.get('min_rate')} ~ {r.get('max_rate')}"
            print(f"  [{'OK' if ok else 'NG'}] {r.get('bank')}: {detail}")

        # ── 보험사 스크레이핑 ─────────────────────────────
        ins_scrapers = [scrape_samsung_life, scrape_samsung_fire]
        ins_scraped  = []
        for fn in ins_scrapers:
            r = await fn(browser)
            ins_scraped.append(r)
            ok = r.get('status') == 'success'
            detail = r.get('message') or f"{r.get('min_rate')} ~ {r.get('max_rate')}"
            print(f"  [{'OK' if ok else 'NG'}] {r.get('bank')}: {detail}")

        # ── 상담사 금리 ───────────────────────────────────
        await scrape_counselor_from_lovable(browser, now)

        # ── KOFIA 금융채 AAA ──────────────────────────────
        print("\n시장금리(KOFIA) 수집 중...")
        kofia_data = await fetch_kofia_fin_bonds(browser, prev_business_day(now))

        await browser.close()

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

    # ── FSS 월별 업데이트 ──────────────────────────────────
    print("\nFSS 월별 금리 수집 시작...")
    update_fss_history(now)

    # ── 시장금리 저장 ──────────────────────────────────────
    print("\n시장금리 저장 중...")
    update_market_rates(now, kofia_data)

    # ── Git commit & push (로컬 실행 시) ─────────────────
    if not os.environ.get('CI'):
        import subprocess
        repo_dir   = os.path.join(BASE_DIR, '..')
        commit_msg = f"chore: update rates {result['updatedAt']}"
        try:
            subprocess.run(['git', 'add',
                            'public/rates.json', 'public/counselor.json',
                            'public/fss.json',   'public/market-rates.json'],
                           cwd=repo_dir, check=True)
            subprocess.run(['git', 'commit', '-m', commit_msg], cwd=repo_dir, check=True)
            subprocess.run(['git', 'push', 'origin', 'master'], cwd=repo_dir, check=True)
            print("[OK] GitHub 푸시 완료")
        except subprocess.CalledProcessError as e:
            print(f"[NG] Git 오류: {e}")


if __name__ == '__main__':
    asyncio.run(main())
