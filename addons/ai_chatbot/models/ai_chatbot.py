import json
import time
import urllib.request
import urllib.error
import re
from datetime import date
from odoo import models, fields, api
from odoo.exceptions import UserError


class AIChatSession(models.Model):
    """
    [MỨC 3 – AI/External API]
    Phiên chatbot AI toàn hệ thống — truy vấn dữ liệu từ cả 3 module.

    Ô nhập câu hỏi + lịch sử hội thoại nằm chung trên form này
    để tránh phải chuyển màn hình sau khi gửi câu hỏi.
    """
    _name = 'ai.chat.session'
    _description = 'Phiên Chat AI'
    _rec_name = 'tieu_de'
    _order = 'create_date desc'

    tieu_de      = fields.Char("Tiêu đề phiên chat", default="Phiên chat mới")
    tin_nhan_ids = fields.One2many('ai.chat.message', 'session_id', string="Lịch sử chat")
    so_tin       = fields.Integer("Số tin nhắn", compute="_compute_so_tin", store=True)
    active       = fields.Boolean("Đang hoạt động", default=True)

    # Ô nhập câu hỏi mới — nằm ngay trên form session
    cau_hoi_moi = fields.Text(
        "Nhập câu hỏi...",
        help="Hỏi bất cứ điều gì về nhân sự, dự án, công việc trong hệ thống"
    )

    @api.depends('tin_nhan_ids')
    def _compute_so_tin(self):
        for r in self:
            r.so_tin = len(r.tin_nhan_ids)

    def action_xoa_lich_su(self):
        self.tin_nhan_ids.unlink()

    def action_phien_moi(self):
        new = self.create({'tieu_de': f"Phiên chat {date.today()}"})
        return {
            'type'     : 'ir.actions.act_window',
            'res_model': self._name,
            'res_id'   : new.id,
            'view_mode': 'form',
            'target'   : 'current',
        }

    # ── Action chính: Gửi tin nhắn ────────────────────────────────
    def action_gui_tin_nhan(self):
        """
        Người dùng gửi câu hỏi → AI trả lời dựa trên dữ liệu hệ thống.
        Chạy trực tiếp trên record ai.chat.session đang mở, không
        chuyển hướng sang model/action khác -> form tự refresh tại chỗ.
        """
        self.ensure_one()
        if not self.cau_hoi_moi or not self.cau_hoi_moi.strip():
            raise UserError("Vui lòng nhập câu hỏi!")

        cau_hoi = self.cau_hoi_moi.strip()
        Message = self.env['ai.chat.message']

        # 1. Lưu tin nhắn người dùng
        Message.create({
            'session_id'   : self.id,
            'loai'         : 'user',
            'noi_dung'     : cau_hoi,
            'noi_dung_html': (
                '<div style="color:#333;white-space:normal;word-break:break-word;'
                'overflow-wrap:anywhere;max-width:100%;box-sizing:border-box;">'
                f'{cau_hoi}</div>'
            ),
        })

        # 2. Lấy lịch sử để gửi kèm (bỏ qua bản ghi rỗng / trùng câu hỏi mới)
        history = [
            {'loai': m.loai, 'noi_dung': m.noi_dung}
            for m in self.tin_nhan_ids.filtered(
                lambda m: m.loai in ('user', 'ai') and m.noi_dung
            )
            if m.noi_dung != cau_hoi
        ]

        # 3. Gọi Gemini API
        tra_loi = Message._goi_gemini(history, cau_hoi)

        # 4. Lưu tin nhắn AI
        html_response = (
            '<div style="font-family:Arial;line-height:1.7;padding:12px;'
            'background:#f0f7ff;border-radius:8px;border-left:4px solid #4a90d9;'
            'white-space:normal;word-break:break-word;overflow-wrap:anywhere;'
            'max-width:100%;box-sizing:border-box;">'
            '<span style="color:#2c5f8a;font-weight:bold;font-size:13px;">🤖 AI:</span><br/><br/>'
            + Message._format_html(tra_loi)
            + '</div>'
        )
        Message.create({
            'session_id'   : self.id,
            'loai'         : 'ai',
            'noi_dung'     : tra_loi,
            'noi_dung_html': html_response,
        })

        # 5. Cập nhật tiêu đề phiên nếu là tin đầu tiên
        if self.so_tin <= 2:
            tieu_de = cau_hoi[:50] + ('...' if len(cau_hoi) > 50 else '')
            self.tieu_de = tieu_de

        # 6. Xóa ô nhập — KHÔNG return action điều hướng.
        # Odoo sẽ tự reload lại đúng record/form hiện tại.
        self.cau_hoi_moi = False
        return True


class AIChatMessage(models.Model):
    """Tin nhắn trong phiên chat AI + các hàm tiện ích gọi Gemini."""
    _name = 'ai.chat.message'
    _description = 'Tin nhắn Chat AI'
    _order = 'create_date asc'

    session_id  = fields.Many2one('ai.chat.session', string="Phiên chat",
                                   required=True, ondelete='cascade')
    loai        = fields.Selection([
        ('user', 'Người dùng'),
        ('ai',   'AI'),
    ], string="Loại", required=True, default='user')
    noi_dung      = fields.Text("Nội dung")
    noi_dung_html = fields.Html("Hiển thị", readonly=True)

    # ── Thu thập toàn bộ dữ liệu hệ thống ─────────────────────────
    @api.model
    def _lay_du_lieu_he_thong(self):
        """
        Thu thập dữ liệu thật từ cả 3 module Odoo để làm context cho AI.
        """
        today = date.today()
        lines = [
            f"=== DỮ LIỆU HỆ THỐNG ERP ODOO (cập nhật: {today}) ===",
            "",
        ]

        # ── 1. MODULE HRM ──────────────────────────────────────────
        # Lưu ý: KHÔNG dùng "if self.env.get('nhan_vien'):" để kiểm tra model
        # có tồn tại hay không -> self.env['nhan_vien'] luôn trả về 1 recordset
        # (dù rỗng), và recordset rỗng luôn là falsy -> điều kiện luôn sai,
        # khiến toàn bộ khối này không bao giờ chạy. Vì nhan_su là dependency
        # bắt buộc của ai_chatbot (khai báo trong __manifest__.py) nên model
        # này chắc chắn tồn tại, gọi thẳng không cần kiểm tra.
        NhanVien = self.env['nhan_vien']
        DonVi    = self.env['don_vi']

        all_nv     = NhanVien.search([])
        dang_lam   = all_nv.filtered(lambda n: n.trang_thai == 'dang_lam')
        tam_nghi   = all_nv.filtered(lambda n: n.trang_thai == 'tam_nghi')
        nghi_viec  = all_nv.filtered(lambda n: n.trang_thai == 'nghi_viec')

        lines += [
            "── MODULE NHÂN SỰ (HRM) ──",
            f"Tổng nhân viên  : {len(all_nv)}",
            f"Đang làm việc   : {len(dang_lam)}",
            f"Tạm nghỉ        : {len(tam_nghi)}",
            f"Đã nghỉ việc    : {len(nghi_viec)}",
            "",
            "Danh sách nhân viên đang làm:",
        ]
        for nv in dang_lam:
            lines.append(
                f"  • {nv.ho_va_ten}"
                f" | {nv.chuc_vu_id.ten_chuc_vu if nv.chuc_vu_id else 'N/A'}"
                f" | {nv.don_vi_id.ten_don_vi if nv.don_vi_id else 'N/A'}"
                f" | {nv.email or ''}"
            )

        don_vi_list = DonVi.search([])
        lines += ["", "Phòng ban / Đơn vị:"]
        for dv in don_vi_list:
            lines.append(
                f"  • {dv.ten_don_vi}: {dv.so_nhan_vien} nhân viên"
                + (f" | Trưởng: {dv.truong_don_vi_id.ho_va_ten}" if dv.truong_don_vi_id else "")
            )

        # ── 2. MODULE DỰ ÁN ────────────────────────────────────────
        DuAn = self.env['du_an']
        all_da      = DuAn.search([])
        dang_tk     = all_da.filtered(lambda d: d.trang_thai == 'dang_trien_khai')
        nhap        = all_da.filtered(lambda d: d.trang_thai == 'nhap')
        hoan_thanh  = all_da.filtered(lambda d: d.trang_thai == 'hoan_thanh')
        tam_dung    = all_da.filtered(lambda d: d.trang_thai == 'tam_dung')

        lines += [
            "",
            "── MODULE QUẢN LÝ DỰ ÁN ──",
            f"Tổng dự án       : {len(all_da)}",
            f"Đang triển khai  : {len(dang_tk)}",
            f"Nháp             : {len(nhap)}",
            f"Tạm dừng         : {len(tam_dung)}",
            f"Hoàn thành       : {len(hoan_thanh)}",
            "",
        ]

        if dang_tk:
            lines.append("Chi tiết dự án đang triển khai:")
            for da in dang_tk:
                tien_do = round(da.tien_do_phan_tram) if da.tien_do_phan_tram else 0
                qua_han = da.so_cv_qua_han if hasattr(da, 'so_cv_qua_han') else 0
                thanh_vien = ', '.join(da.thanh_vien_ids.mapped('ho_va_ten'))
                lines.append(
                    f"  • [{da.ma_du_an}] {da.ten_du_an}"
                    f"\n    Trưởng: {da.truong_du_an_id.ho_va_ten if da.truong_du_an_id else 'N/A'}"
                    f"\n    Thành viên: {thanh_vien or 'Chưa có'}"
                    f"\n    Tiến độ: {tien_do}% | CV quá hạn: {qua_han}"
                    f"\n    Deadline: {da.ngay_ket_thuc}"
                )

        # ── 3. MODULE CÔNG VIỆC ────────────────────────────────────
        CongViec      = self.env['cong_viec']
        all_cv        = CongViec.search([])
        chua_bd       = all_cv.filtered(lambda c: c.trang_thai == 'chua_bat_dau')
        dang_lam_cv   = all_cv.filtered(lambda c: c.trang_thai == 'dang_thuc_hien')
        qua_han_cv    = all_cv.filtered(lambda c: c.la_qua_han and c.trang_thai != 'hoan_thanh')
        hoan_thanh_cv = all_cv.filtered(lambda c: c.trang_thai == 'hoan_thanh')

        lines += [
            "",
            "── MODULE QUẢN LÝ CÔNG VIỆC ──",
            f"Tổng công việc   : {len(all_cv)}",
            f"Chưa bắt đầu    : {len(chua_bd)}",
            f"Đang thực hiện  : {len(dang_lam_cv)}",
            f"Hoàn thành      : {len(hoan_thanh_cv)}",
            f"⚠️ Quá hạn      : {len(qua_han_cv)}",
        ]

        if qua_han_cv:
            lines += ["", "Công việc quá hạn cần chú ý:"]
            for cv in qua_han_cv[:10]:
                lines.append(
                    f"  ⚠️ {cv.ten_cong_viec}"
                    f" | PH: {cv.nguoi_phu_trach_id.ho_va_ten if cv.nguoi_phu_trach_id else 'N/A'}"
                    f" | Deadline: {cv.deadline}"
                    f" | Dự án: {cv.du_an_id.ten_du_an if cv.du_an_id else 'Không có'}"
                )

        if all_cv:
            lines += ["", "Khối lượng công việc theo nhân viên:"]
            nv_stats = {}
            for cv in all_cv.filtered(lambda c: c.trang_thai not in ('hoan_thanh', 'huy')):
                nv = cv.nguoi_phu_trach_id
                if nv:
                    if nv.id not in nv_stats:
                        nv_stats[nv.id] = {'ten': nv.ho_va_ten, 'tong': 0, 'qua_han': 0}
                    nv_stats[nv.id]['tong'] += 1
                    if cv.la_qua_han:
                        nv_stats[nv.id]['qua_han'] += 1
            for stat in sorted(nv_stats.values(), key=lambda x: -x['tong']):
                lines.append(
                    f"  • {stat['ten']}: {stat['tong']} việc đang làm"
                    + (f" ({stat['qua_han']} quá hạn ⚠️)" if stat['qua_han'] else "")
                )

        return '\n'.join(lines)

    # ── Gọi Gemini API ─────────────────────────────────────────────
    @api.model
    def _goi_gemini(self, messages_history, cau_hoi_moi):
        """
        Gọi Google Gemini API với lịch sử hội thoại (multi-turn chat).
        Tự động retry 1 lần nếu gặp lỗi 503 (server quá tải tạm thời).
        """
        config = self.env['ai.config'].search([('active', '=', True)], limit=1)
        api_key = config.gemini_api_key if config else ''
        if not api_key:
            api_key = self.env['ir.config_parameter'].sudo().get_param('gemini.api_key', '')
        if not api_key:
            raise UserError(
                "Chưa cấu hình Gemini API Key!\n\n"
                "Cách lấy miễn phí:\n"
                "1. Vào: https://aistudio.google.com/apikey\n"
                "2. Đăng nhập Google → Create API Key\n"
                "3. Vào menu 'Cấu hình AI' → nhập key vào"
            )

        model = config.model_ai if config else 'gemini-2.5-flash'

        du_lieu_he_thong = self._lay_du_lieu_he_thong()

        system_prompt = f"""Bạn là trợ lý AI thông minh của hệ thống ERP nội bộ công ty, tích hợp với Odoo 15.
Bạn có quyền truy cập dữ liệu thời gian thực từ 3 module: Nhân sự (HRM), Quản lý Dự án, Quản lý Công việc.

{du_lieu_he_thong}

=== HƯỚNG DẪN TRẢ LỜI ===
- Trả lời bằng tiếng Việt, thân thiện và chuyên nghiệp
- Dựa trên dữ liệu thật ở trên, KHÔNG đoán mò
- Nếu không có dữ liệu liên quan, nói rõ "Hệ thống chưa có thông tin về..."
- Đề xuất giải pháp cụ thể khi phát hiện vấn đề (quá hạn, thiếu nhân lực...)
- Dùng emoji phù hợp để dễ đọc"""

        contents = []
        for msg in messages_history[-10:]:
            if not msg.get('noi_dung'):
                continue
            role = "user" if msg['loai'] == 'user' else "model"
            contents.append({"role": role, "parts": [{"text": msg['noi_dung']}]})
        contents.append({"role": "user", "parts": [{"text": cau_hoi_moi}]})

        payload = json.dumps({
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents"          : contents,
            "generationConfig"  : {
                "temperature"    : 0.7,
                "maxOutputTokens": 2000,
            }
        }).encode('utf-8')

        def _call(model_name):
            call_url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model_name}:generateContent?key={api_key}"
            )
            req = urllib.request.Request(
                call_url, data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                return result['candidates'][0]['content']['parts'][0]['text']

        # Danh sách model thử lần lượt: model đã chọn -> các model dự phòng nhẹ hơn
        models_to_try = [model]
        for fallback in ('gemini-2.5-flash-lite', 'gemini-2.5-flash'):
            if fallback not in models_to_try:
                models_to_try.append(fallback)

        last_error = None
        for model_name in models_to_try:
            # Với mỗi model: thử tối đa 3 lần, backoff tăng dần (1s, 2s, 4s)
            delay = 1
            for attempt in range(3):
                try:
                    return _call(model_name)
                except urllib.error.HTTPError as e:
                    body = e.read().decode('utf-8')
                    try:
                        err_msg = json.loads(body).get('error', {}).get('message', body)
                    except Exception:
                        err_msg = body
                    last_error = (e.code, err_msg)
                    if e.code == 503:
                        time.sleep(delay)
                        delay *= 2
                        continue  # thử lại cùng model
                    else:
                        # Lỗi khác 503 (400, 403, 404...) -> không có ích khi retry
                        raise UserError(f"Lỗi Gemini API ({e.code}): {err_msg}")
                except urllib.error.URLError as e:
                    raise UserError(f"Không kết nối được Gemini: {str(e.reason)}")
            # Hết 3 lần thử với model này vẫn 503 -> chuyển sang model dự phòng tiếp theo

        # Đã thử hết mọi model, mọi lần retry đều thất bại
        code, msg = last_error if last_error else (503, "Không rõ lỗi")
        raise UserError(
            f"Lỗi Gemini API ({code}): {msg}\n\n"
            "Server Google đang quá tải kéo dài (đã tự thử lại nhiều lần và "
            "nhiều model khác nhau). Vui lòng đợi vài phút rồi thử lại, "
            "hoặc kiểm tra: https://aistudio.google.com/status"
        )

    # ── Format AI response sang HTML ──────────────────────────────
    @staticmethod
    def _format_html(text):
        """Chuyển markdown của Gemini sang HTML đẹp."""
        html = ''
        for line in text.split('\n'):
            s = line.strip()
            if not s:
                html += '<br/>'
            elif s.startswith('### '):
                html += f'<h4 style="color:#2c5f8a;margin:8px 0 4px">{s[4:]}</h4>'
            elif s.startswith('## '):
                html += f'<h3 style="color:#2c5f8a;margin:10px 0 5px">{s[3:]}</h3>'
            elif re.match(r'^\*\*(.+)\*\*$', s):
                html += f'<b>{s[2:-2]}</b><br/>'
            elif s.startswith('* ') or s.startswith('- '):
                html += f'<div style="margin:2px 0 2px 12px">• {s[2:]}</div>'
            elif re.match(r'^\d+\.', s):
                html += f'<div style="margin:2px 0 2px 12px">{s}</div>'
            else:
                s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
                html += f'<div style="margin:2px 0">{s}</div>'
        return html