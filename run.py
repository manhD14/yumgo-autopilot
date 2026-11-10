"""Yumgo Autopilot: mở file index.html trong trình duyệt ẩn, kéo dữ liệu từ Firebase, xử lý yêu cầu của shipper
(đăng ký / xin nghỉ / đổi ca / nhận ca) + tự xếp lịch tuần sau (nếu bật), rồi đẩy kết quả lên lại.
Dùng CHÍNH logic của index.html nên kết quả giống hệt khi bạn mở file bằng tay."""
import os, sys
from playwright.sync_api import sync_playwright

JS = """
async (code) => {
  const out = {};
  meta.cloud = CLOUD_DB + '/yumgo/' + await cKey(code); meta.code = code; meta.base = 0; meta.cd = 0; saveMeta();
  const rev = await cGet('/rev');
  if (rev == null) return {err: 'Firebase chưa có dữ liệu cho mã này - dừng để không ghi đè. Kiểm tra lại SYNC_CODE.'};
  let synced = false;
  for (let i = 0; i < 3; i++) {
    await cPull(); cReady = false;
    const before = JSON.stringify(S);
    await pubSync(); autoRun(); clearTimeout(pt);
    if (JSON.stringify(S) === before) { out.changed = false; synced = true; break; }
    const r = await cGet('/rev');
    if (r === meta.base) { await cPush(); out.changed = true; synced = true; break; }
    out.retry = i + 1;
  }
  if (!synced) return {err: 'Bạn đang chỉnh dữ liệu cùng lúc - bỏ qua lượt này, lượt sau sẽ thử lại.'};
  pubInfo.rt = Date.now(); await pubPush();
  out.events = pubInfo.n; out.perr = pubInfo.err || '';
  return out;
}
"""

def main(route=None, app=None):
    code = os.environ.get('SYNC_CODE', '').strip()
    if len(code) < 8:
        print('Thiếu SYNC_CODE (mã đồng bộ) trong GitHub Secrets'); return 1
    app = app or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'index.html')
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(timezone_id='Asia/Ho_Chi_Minh', locale='vi-VN')
        if route: ctx.route('**/*', route)
        pg = ctx.new_page(); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto('file://' + app); pg.wait_for_timeout(800)
        res = pg.evaluate(JS, code)
        b.close()
    print({k: v for k, v in res.items()}, 'page_errors:', len(errs))
    if errs: print(errs[:3])
    return 1 if res.get('err') or res.get('perr') else 0

if __name__ == '__main__':
    sys.exit(main())
