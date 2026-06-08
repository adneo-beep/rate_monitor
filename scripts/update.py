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
    카카오뱅크 - '금리정보' 탭 클릭 → '5년 변동 금리 대출' 기준 (예: 4.944 ~ 7.01)
    ※ 폴백 최소금리 사용 금지 – '5년 변동' 섹션에서만 추출
    """
    page = await browser.new_page()
    try:
        await page.goto("https://www.kakaobank.com/products/mortgageLoan", timeout=30000)
        await page.wait_for_load_state("networkidle", timeout=20000)
        await page.wait_for_timeout(2000)

        # 스크롤하면서 '금리정보' 버튼/탭 찾아 클릭
        for scroll_pct in [0.5, 0.7, 0.9, 1.0]:
            await page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {scroll_pct})")
            await page.wait_for_timeout(800)
            for selector in [
                'button:has-text("금리정보")',
                'a:has-text("금리정보")',
                'span:has-text("금리정보")',
                'li:has-text("금리정보")',
            ]:
                try:
                    el = await page.query_selector(selector)
                    if el and await el.is_visible():
                        await el.click()
                        await page.wait_for_timeout(2000)
                        break
                except Exception:
                    pass

        data = await page.evaluate("""() => {
            const body = document.body.innerText || '';
            const lines = body.split(/[\\n\\r]+/).map(l => l.trim()).filter(Boolean);

            // ① '5년 변동 금리 대출' 섹션에서 금리 범위 찾기
            for (let i = 0; i < lines.length; i++) {
                const line = lines[i];
                if ((line.includes('5년') && line.includes('변동')) ||
                     line.includes('5년 변동 금리')) {
                    const area = lines.slice(i, Math.min(lines.length, i + 8)).join(' ');
                    // 연 4.944% ~ 7.01% 또는 4.944 ~ 7.01 패턴
                    const m = area.match(/([3-9]\\.[0-9]{2,3})\\s*%?\\s*[~\\-]\\s*([3-9]\\.[0-9]{2,3})\\s*%?/);
                    if (m) return { min_rate: m[1], max_rate: m[2], found: '5년변동' };
                }
            }

            // ② 테이블에서 '5년 변동' 행 찾기
            for (const row of document.querySelectorAll('table tr, [class*="row"]')) {
                const txt = row.innerText || '';
                if (txt.includes('5년') && txt.includes('변동')) {
                    const m = txt.match(/([3-9]\\.[0-9]{2,3})\\s*[~\\-]\\s*([3-9]\\.[0-9]{2,3})/);
                    if (m) return { min_rate: m[1], max_rate: m[2], found: '테이블' };
                }
            }
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
    케이뱅크 - '금리안내' 클릭 → '주기형 금리(금융채 5년)' 최저·최고 (예: 4.56 ~ 8.44)
    ※ '주기형' 섹션에서만 추출 – 전체 페이지 최솟값 사용 금지
    """
    page = await browser.new_page()
    try:
        await page.goto(
            "https://www.kbanknow.com/ib20/mnu/FPMLON250000?phashid=sAySEh8",
            timeout=30000)
        await page.wait_for_load_state("networkidle", timeout=20000)
        await page.wait_for_timeout(2000)

        # 스크롤하면서 '금리안내' 버튼/탭 클릭
        for scroll_pct in [0.5, 0.7, 0.9, 1.0]:
            await page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {scroll_pct})")
            await page.wait_for_timeout(800)
            for selector in [
                'button:has-text("금리안내")',
                'a:has-text("금리안내")',
                'span:has-text("금리안내")',
                'li:has-text("금리안내")',
            ]:
                try:
                    el = await page.query_selector(selector)
                    if el and await el.is_visible():
                        await el.click()
                        await page.wait_for_timeout(2500)
                        break
                except Exception:
                    pass

        data = await page.evaluate("""() => {
            // ① 테이블에서 '주기형' + '금융채 5년' 행 탐색
            for (const row of document.querySelectorAll('table tr')) {
                const txt = row.innerText || row.textContent || '';
                if ((txt.includes('주기형') && (txt.includes('금융채') || txt.includes('5년'))) ||
                     txt.includes('주기형 금리')) {
                    const cells = [...row.querySelectorAll('td')];
                    // 4.XX 이상의 값만 허용 (전세/기타 저금리 제외)
                    const nums = cells
                        .map(c => parseFloat((c.innerText || c.textContent || '').replace('%','').trim()))
                        .filter(n => !isNaN(n) && n >= 4.0 && n < 15);
                    if (nums.length >= 2) {
                        return { min_rate: String(Math.min(...nums)), max_rate: String(Math.max(...nums)) };
                    }
                }
            }

            // ② 텍스트에서 '주기형' 줄 근처 금리 범위 찾기
            const body = document.body.innerText || '';
            const lines = body.split(/[\\n\\r]+/).map(l => l.trim()).filter(Boolean);
            for (let i = 0; i < lines.length; i++) {
                const line = lines[i];
                if (line.includes('주기형') && (line.includes('금융채') || line.includes('5년'))) {
                    const area = lines.slice(i, Math.min(lines.length, i + 10)).join(' ');
                    const m = area.match(/([4-9]\\.[0-9]{2,3})\\s*[~\\-]\\s*([4-9]\\.[0-9]{2,3})/);
                    if (m) return { min_rate: m[1], max_rate: m[2] };
                }
            }
            return null;
        }""")

        if data and data.get('min_rate'):
            return {'bank': '케이뱅크', 'product': '케이뱅크 아파트담보대출 주기형(금융채 5년)',
                    'min_rate': data['min_rate'], 'max_rate': data.get('max_rate', '-'), 'status': 'success'}
        return {'bank': '케이뱅크', 'status': 'error', 'message': '주기형 금리 섹션 없음'}
    except Exception as e:
        return {'bank': '케이뱅크', 'status': 'error', 'message': str(e)[:100]}
    finally:
        await page.close()


# ══════════════════════════════════════════════════════════
#  보험사 스크레이퍼 (신규)
# ══════════════════════════════════════════════════════════

async def scrape_samsung_life(browser):
    """삼성생명 주택담보대출 - 5년 주기형 기준"""
    page = await browser.new_page()
    try:
        # 삼성생명 모바일 주담대 상품 페이지
        await page.goto("https://www.samsunglife.com/individual/products/loan/detail/F34820",
                        timeout=30000)
        await page.wait_for_load_state("networkidle", timeout=20000)
        await page.wait_for_timeout(2000)

        # '금리안내' 탭 클릭 시도
        for selector in [
            'button:has-text("금리안내")', 'a:has-text("금리안내")',
            'button:has-text("금리")',     'li:has-text("금리안내")',
        ]:
            try:
                el = await page.query_selector(selector)
                if el:
                    await el.click()
                    await page.wait_for_timeout(2000)
                    break
            except Exception:
                pass

        data = await page.evaluate("""() => {
            const body = document.body.innerText || '';
            const lines = body.split(/[\\n\\r]+/).map(l => l.trim()).filter(Boolean);

            // '5년 주기형' 또는 '5년' 금리 찾기
            for (let i = 0; i < lines.length; i++) {
                const line = lines[i];
                if (line.includes('5년') && (line.includes('주기') || line.includes('변동') || line.includes('고정'))) {
                    const area = lines.slice(Math.max(0, i-1), Math.min(lines.length, i+8)).join(' ');
                    const m = area.match(/([3-9]\\.\\d{2,3})\\s*%?\\s*~\\s*([3-9]\\.\\d{2,3})\\s*%?/);
                    if (m) return { min_rate: m[1], max_rate: m[2] };
                }
            }

            // 폴백: 연 X.XX% ~ Y.YY% 패턴
            const m1 = body.match(/연\\s*([3-9]\\.\\d{2,3})\\s*%?\\s*~\\s*연?\\s*([3-9]\\.\\d{2,3})\\s*%/);
            if (m1) return { min_rate: m1[1], max_rate: m1[2] };

            const m2 = body.match(/([3-9]\\.\\d{2,3})\\s*%\\s*~\\s*([3-9]\\.\\d{2,3})\\s*%/);
            if (m2) return { min_rate: m2[1], max_rate: m2[2] };

            return null;
        }""")

        if data and data.get('min_rate'):
            return {'bank': '삼성생명', 'product': '삼성생명 주담대 (5년 주기형)',
                    'min_rate': data['min_rate'], 'max_rate': data.get('max_rate'), 'status': 'success'}
        return {'bank': '삼성생명', 'status': 'error', 'message': '금리 데이터 없음'}
    except Exception as e:
        return {'bank': '삼성생명', 'status': 'error', 'message': str(e)[:100]}
    finally:
        await page.close()


async def scrape_samsung_fire(browser):
    """삼성화재 주택담보대출 금리"""
    page = await browser.new_page()
    try:
        await page.goto("https://www.samsungfire.com/loan/P_P04_04_01_066.html", timeout=30000)
        await page.wait_for_load_state("networkidle", timeout=20000)
        await page.wait_for_timeout(2000)

        # '금리안내' 또는 '한도/금리 확인' 버튼 클릭 시도
        for selector in [
            'button:has-text("금리안내")', 'a:has-text("금리안내")',
            'button:has-text("금리")',     'a:has-text("한도/금리")',
            'button:has-text("한도")',
        ]:
            try:
                el = await page.query_selector(selector)
                if el:
                    await el.click()
                    await page.wait_for_timeout(2000)
                    break
            except Exception:
                pass

        data = await page.evaluate("""() => {
            const body = document.body.innerText || '';

            // 금리 범위 패턴
            const patterns = [
                /([3-9]\\.\\d{2,3})\\s*%\\s*~\\s*([3-9]\\.\\d{2,3})\\s*%/,
                /연\\s*([3-9]\\.\\d{2,3})\\s*%?\\s*~\\s*([3-9]\\.\\d{2,3})/,
                /최저\\s*연?\\s*([3-9]\\.\\d{2,3})/,
            ];

            for (const pat of patterns) {
                const m = body.match(pat);
                if (m) return { min_rate: m[1], max_rate: m[2] || null };
            }
            return null;
        }""")

        if data and data.get('min_rate'):
            return {'bank': '삼성화재', 'product': '삼성화재 주택담보대출',
                    'min_rate': data['min_rate'], 'max_rate': data.get('max_rate'), 'status': 'success'}
        return {'bank': '삼성화재', 'status': 'error', 'message': '금리 데이터 없음'}
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
    1단계: 직접 API 호출 시도
    2단계: Playwright 스크레이핑
    """
    date_str = prev_day.strftime('%Y%m%d')
    result = {}

    # ── 1단계: 직접 HTTP API 시도 ──────────────────────────
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/125.0.0.0 Safari/537.36',
        'Referer':    'https://www.kofiabond.or.kr/',
        'Accept':     'application/json, text/javascript, */*; q=0.01',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest',
    }

    # 알려진 KOFIA API 엔드포인트 패턴 순서대로 시도
    api_attempts = [
        {
            'url':    'https://www.kofiabond.or.kr/publicData/getDiscountCurveInfo.json',
            'params': f'workDate={date_str}&typecode=4'.encode(),  # typecode 4 = 금융채
        },
        {
            'url':    'https://www.kofiabond.or.kr/BondSta/getBondGrpSrtPrcInfo.json',
            'params': f'workDate={date_str}&bondKndCd=F&bondGrpCd=FA'.encode(),
        },
        {
            'url':    'https://www.kofiabond.or.kr/BondGrpSta/getBondGrpSrtPrcInfo.json',
            'params': f'workDate={date_str}&gubun=4'.encode(),
        },
    ]

    TERM_MAP = {0.5: 'fin6m', 1.0: 'fin1y', 3.0: 'fin3y', 5.0: 'fin5y'}
    TERM_LABELS = {'6M': 'fin6m', '1Y': 'fin1y', '3Y': 'fin3y', '5Y': 'fin5y',
                   '0.5': 'fin6m', '1': 'fin1y', '3': 'fin3y', '5': 'fin5y'}

    for attempt in api_attempts:
        try:
            req = urllib.request.Request(
                attempt['url'], data=attempt['params'], headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=10) as r:
                raw = r.read().decode('utf-8', errors='replace')
            if not raw or raw.strip().startswith('<'):
                continue
            j = json.loads(raw)
            items = j if isinstance(j, list) else j.get('result') or j.get('data') or []
            if not items:
                continue
            for item in items:
                # term 필드 추출 (다양한 키 이름 처리)
                term_raw = str(item.get('term') or item.get('TERM') or
                               item.get('mtrtyTrm') or item.get('maturity') or '')
                rate_raw = (item.get('yield') or item.get('YIELD') or
                            item.get('rate') or item.get('RATE') or
                            item.get('srPrc') or '')
                if not term_raw or not rate_raw:
                    continue
                try:
                    term_f = float(term_raw)
                    rate_f = round(float(str(rate_raw).replace('%', '')), 3)
                    key = TERM_MAP.get(term_f)
                    if key:
                        result[key] = rate_f
                except Exception:
                    pass
            if result:
                print(f'    KOFIA API 성공 ({attempt["url"].split("/")[-1]}): {result}')
                return result
        except Exception as e:
            print(f'    KOFIA API 실패 ({attempt["url"].split("/")[-1]}): {e}')

    # ── 2단계: Playwright 스크레이핑 ───────────────────────
    print('    KOFIA Playwright 스크레이핑 시도...')
    page = await browser.new_page()
    try:
        # 채권시가평가수익률 페이지 직접 이동
        kofia_url = (
            'https://www.kofiabond.or.kr/websquare/websquare.html'
            '?w2xPath=/xml/subMain.xml'
            '&divisionId=MBIS01040010000000'
            '&parentDivisionId=MBIS01040000000000'
            '&parentMenuIndex=3&menuIndex=0'
        )
        await page.goto(kofia_url, timeout=60000, wait_until='domcontentloaded')
        # WebSquare 렌더링 대기
        await page.wait_for_timeout(25000)

        dom_data = await page.evaluate("""() => {
            const body = document.body;
            if (!body || body.innerHTML.length < 500) return null;

            const allText = (body.innerText || body.textContent || '');
            const lines = allText.split(/[\\n\\r]+/).map(l => l.trim()).filter(Boolean);

            // 금융채Ⅰ(은행채) 무보증 AAA 행 찾기
            for (let i = 0; i < lines.length; i++) {
                const line = lines[i];
                if ((line.includes('금융채') || line.includes('은행채')) &&
                    (line.includes('AAA') || line.includes('무보증'))) {

                    // 해당 줄 및 다음 20줄에서 금리 추출
                    const area = lines.slice(i, Math.min(lines.length, i + 20)).join(' ');
                    const nums = [...area.matchAll(/([2-9]\\.\\d{2,3})/g)]
                        .map(m => parseFloat(m[1]))
                        .filter(n => n > 0.5 && n < 15)
                        .sort((a, b) => a - b);

                    // 만기 오름차순: 6개월, 1년, 3년, 5년
                    if (nums.length >= 4) {
                        return { fin6m: nums[0], fin1y: nums[1], fin3y: nums[2], fin5y: nums[3] };
                    } else if (nums.length >= 2) {
                        return { fin6m: nums[0], fin5y: nums[nums.length - 1] };
                    }
                }
            }

            // 테이블 구조에서 직접 추출
            for (const table of document.querySelectorAll('table')) {
                for (const row of table.querySelectorAll('tr')) {
                    const rowText = row.innerText || row.textContent || '';
                    if ((rowText.includes('금융채') || rowText.includes('은행채')) &&
                         rowText.includes('AAA')) {
                        const cells = [...row.querySelectorAll('td')];
                        const nums = cells
                            .map(c => parseFloat((c.innerText || c.textContent || '').trim()))
                            .filter(n => !isNaN(n) && n > 0.5 && n < 15)
                            .sort((a, b) => a - b);
                        if (nums.length >= 4) {
                            return { fin6m: nums[0], fin1y: nums[1], fin3y: nums[2], fin5y: nums[3] };
                        }
                    }
                }
            }
            return null;
        }""")

        if dom_data and dom_data.get('fin6m'):
            print(f'    KOFIA Playwright 성공: {dom_data}')
            return dom_data
        else:
            print(f'    KOFIA Playwright: 데이터 없음 (bodyLen={await page.evaluate("document.body?.innerHTML?.length||0")})')

    except Exception as e:
        print(f'    KOFIA Playwright 실패: {e}')
    finally:
        await page.close()

    return {}


def update_market_rates(now, kofia_data: dict):
    """
    BOK(국고채) + KOFIA(금융채 AAA) 데이터로 market-rates.json 업데이트
    기준: 전일 영업일 마감
    """
    prev_day = prev_business_day(now)

    def fetch_bok_rate(item_code):
        """BOK ECOS API - 전일 기준 최신값"""
        end_d   = prev_day.strftime('%Y%m%d')
        start_d = (prev_day - timedelta(days=7)).strftime('%Y%m%d')
        url = (f'{BOK_BASE}/StatisticSearch/{BOK_API_KEY}/json/kr/1/10'
               f'/817Y002/D/{start_d}/{end_d}/{item_code}')
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                j = json.loads(r.read().decode('utf-8'))
            rows = [x for x in (j.get('StatisticSearch', {}).get('row') or [])
                    if x.get('DATA_VALUE') and x['DATA_VALUE'] != '-']
            if rows:
                return round(float(rows[-1]['DATA_VALUE']), 3)
        except Exception as e:
            print(f'    BOK fetch error ({item_code}): {e}')
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
        change  = round(new_val - old_val, 3) if new_val is not None and old_val is not None else None
        return {'label': label, 'value': new_val, 'change': change}

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
            s = s.strip().replace('%', '')
            try:
                return round(float(s), 3)
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

        updated_at = date_str.replace('-', '.') + ' 기준' if date_str else now.strftime('%Y.%m.%d 기준')
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
        commit_msg = f"chore: update rates {result['updatedAt']} [skip ci]"
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
