import json
import urllib.request
import urllib.error
from odoo import models, fields, api
from odoo.exceptions import UserError


class WizardAIDuAn(models.TransientModel):
    """
    [MỨC 3 – Tích hợp AI – Google Gemini FREE]
    Wizard AI phân tích dự án sử dụng Google Gemini API (miễn phí).

    Lấy API key miễn phí tại: https://aistudio.google.com/apikey
    Giới hạn: 1,500 requests/ngày, không cần thẻ tín dụng.

    Tính năng 1 – Chatbot hỏi đáp:
        Input : câu hỏi + dữ liệu dự án thật từ Odoo
        Xử lý : gửi lên Gemini API với context dự án
        Output: phân tích tiếng Việt, ghi log chatter dự án

    Tính năng 2 – AI đề xuất phân công:
        Input : thông tin thành viên (chức vụ từ HRM) + yêu cầu
        Xử lý : Gemini phân tích, trả JSON danh sách công việc
        Output: tự động tạo cong_viec trong Odoo, gán đúng người
    """
    _name = 'wizard.ai_du_an'
    _description = 'AI Phân tích Dự án (Google Gemini)'

    du_an_id = fields.Many2one('du_an', string="Dự án", required=True, ondelete='cascade')
    api_key  = fields.Char(
        "Google Gemini API Key",
        help="Lấy miễn phí tại https://aistudio.google.com/apikey — dạng AIzaSy..."
    )
    che_do = fields.Selection([
        ('chatbot',   '💬 Hỏi đáp về dự án'),
        ('phan_cong', '🤖 AI đề xuất phân công công việc'),
    ], string="Chế độ AI", default='chatbot', required=True)

    # ── Chatbot ────────────────────────────────────────────────────
    cau_hoi = fields.Text(
        "Câu hỏi của bạn",
        placeholder="VD: Dự án đang tiến độ thế nào? / Ai đang có việc quá hạn? / Đề xuất cải thiện?"
    )
    tra_loi = fields.Html("Trả lời từ AI", readonly=True)

    # ── Phân công ──────────────────────────────────────────────────
    yeu_cau_pc = fields.Text(
        "Yêu cầu phân công",
        placeholder="VD: Tạo công việc phù hợp với chức vụ từng thành viên, tập trung giai đoạn phát triển"
    )
    ket_qua_pc = fields.Html("Kết quả AI đề xuất", readonly=True)
    da_tao_cv  = fields.Boolean("Đã tạo công việc?", default=False)

    # ── Context dữ liệu dự án ─────────────────────────────────────
    thong_tin_du_an = fields.Text("Dữ liệu dự án gửi cho AI", readonly=True)

    @api.onchange('du_an_id', 'che_do')
    def _onchange_du_an(self):
        if self.du_an_id:
            self.thong_tin_du_an = self._lay_thong_tin_du_an()

    # ── Thu thập dữ liệu dự án từ Odoo ────────────────────────────
    def _lay_thong_tin_du_an(self):
        da = self.du_an_id
        CongViec = self.env.get('cong_viec')

        trang_thai_label = dict(da._fields['trang_thai'].selection).get(da.trang_thai, da.trang_thai)

        lines = [
            "=== THÔNG TIN DỰ ÁN (từ Odoo ERP) ===",
            f"Tên dự án    : {da.ten_du_an}",
            f"Mã dự án     : {da.ma_du_an}",
            f"Trạng thái   : {trang_thai_label}",
            f"Ngày bắt đầu : {da.ngay_bat_dau}",
            f"Ngày kết thúc: {da.ngay_ket_thuc}",
            f"Khách hàng   : {da.khach_hang or 'Nội bộ'}",
            f"Độ ưu tiên   : {da.do_uu_tien}",
            "",
            "=== NHÂN SỰ (từ module HRM) ===",
            f"Trưởng dự án : {da.truong_du_an_id.ho_va_ten if da.truong_du_an_id else 'Chưa có'}",
            f"  Chức vụ    : {da.truong_du_an_id.chuc_vu_id.ten_chuc_vu if da.truong_du_an_id and da.truong_du_an_id.chuc_vu_id else 'N/A'}",
            f"  Phòng ban  : {da.truong_du_an_id.don_vi_id.ten_don_vi if da.truong_du_an_id and da.truong_du_an_id.don_vi_id else 'N/A'}",
            "",
            "Danh sách thành viên:",
        ]

        for nv in da.thanh_vien_ids:
            cv_label = nv.chuc_vu_id.ten_chuc_vu if nv.chuc_vu_id else 'N/A'
            dv_label = nv.don_vi_id.ten_don_vi if nv.don_vi_id else 'N/A'
            lines.append(f"  - {nv.ho_va_ten} | Chức vụ: {cv_label} | Phòng ban: {dv_label}")

        if CongViec:
            all_cv = CongViec.search([('du_an_id', '=', da.id)])
            if all_cv:
                lines += ["", "=== CÔNG VIỆC HIỆN TẠI ==="]
                for cv in all_cv:
                    tt = dict(cv._fields['trang_thai'].selection).get(cv.trang_thai, cv.trang_thai)
                    qh = " ⚠️ QUÁ HẠN" if cv.la_qua_han else ""
                    lines.append(
                        f"  [{tt}]{qh} {cv.ten_cong_viec}"
                        f" | Phụ trách: {cv.nguoi_phu_trach_id.ho_va_ten}"
                        f" | Deadline: {cv.deadline}"
                    )
                done    = all_cv.filtered(lambda c: c.trang_thai == 'hoan_thanh')
                overdue = all_cv.filtered(lambda c: c.la_qua_han)
                pct     = round(len(done) / len(all_cv) * 100) if all_cv else 0
                lines += [
                    "",
                    f"Tổng công việc : {len(all_cv)}",
                    f"Đã hoàn thành  : {len(done)}",
                    f"Quá hạn        : {len(overdue)}",
                    f"Tiến độ        : {pct}%",
                ]
            else:
                lines.append("\n(Dự án chưa có công việc nào)")

        return '\n'.join(lines)

    # ── Gọi Google Gemini API ──────────────────────────────────────
    def _goi_gemini_api(self, prompt):
        """
        Gọi Google Gemini API (miễn phí).
        Model: gemini-1.5-flash — nhanh, free 1500 req/ngày.
        """
        api_key = (
            self.api_key
            or self.env['ir.config_parameter'].sudo().get_param('gemini.api_key', '')
        )
        if not api_key:
            raise UserError(
                "Chưa có Gemini API Key!\n\n"
                "Cách lấy miễn phí (2 phút):\n"
                "1. Vào https://aistudio.google.com/apikey\n"
                "2. Đăng nhập Google\n"
                "3. Bấm 'Create API Key' → Copy key\n"
                "4. Dán vào ô 'Google Gemini API Key' ở trên"
            )

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-1.5-flash:generateContent?key={api_key}"
        )
        payload = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature"    : 0.7,
                "maxOutputTokens": 1500,
            }
        }).encode('utf-8')

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                return result['candidates'][0]['content']['parts'][0]['text']
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8')
            try:
                err_msg = json.loads(body).get('error', {}).get('message', body)
            except Exception:
                err_msg = body
            raise UserError(f"Lỗi Gemini API ({e.code}): {err_msg}")
        except urllib.error.URLError as e:
            raise UserError(f"Không kết nối được: {str(e.reason)}")
        except Exception as e:
            raise UserError(f"Lỗi không xác định: {str(e)}")

    # ── Tính năng 1: Chatbot hỏi đáp ─────────────────────────────
    def action_hoi_ai(self):
        self.ensure_one()
        if not self.cau_hoi:
            raise UserError("Vui lòng nhập câu hỏi!")

        thong_tin = self._lay_thong_tin_du_an()

        prompt = f"""Bạn là trợ lý quản lý dự án thông minh của công ty, sử dụng dữ liệu thật từ hệ thống ERP Odoo.

{thong_tin}

=== CÂU HỎI CỦA QUẢN LÝ ===
{self.cau_hoi}

Hãy trả lời bằng tiếng Việt, ngắn gọn và rõ ràng. Nếu phát hiện vấn đề (quá hạn, chậm tiến độ...) hãy đề xuất giải pháp cụ thể."""

        answer = self._goi_gemini_api(prompt)

        # Format HTML đẹp
        html  = '<div style="font-family:Arial;line-height:1.8;padding:14px;'
        html += 'background:#f0f7ff;border-radius:8px;border-left:4px solid #4a90d9;">'
        html += '<b style="color:#2c5f8a;font-size:14px;">🤖 Gemini AI trả lời:</b><br/><br/>'
        for line in answer.split('\n'):
            stripped = line.strip()
            if not stripped:
                html += '<br/>'
            elif stripped.startswith('**') and stripped.endswith('**'):
                html += f'<b>{stripped[2:-2]}</b><br/>'
            elif stripped.startswith('* ') or stripped.startswith('- '):
                html += f'&nbsp;&nbsp;• {stripped[2:]}<br/>'
            else:
                html += f'{stripped}<br/>'
        html += '</div>'

        self.tra_loi        = html
        self.thong_tin_du_an = thong_tin

        # Ghi log vào chatter dự án
        self.du_an_id.message_post(
            body=(
                f"🤖 <b>AI được hỏi:</b> {self.cau_hoi}<br/>"
                f"<b>AI trả lời:</b> {answer[:400]}..."
                if len(answer) > 400 else
                f"🤖 <b>AI được hỏi:</b> {self.cau_hoi}<br/><b>AI trả lời:</b> {answer}"
            )
        )

        return self._reopen()

    # ── Tính năng 2: AI đề xuất phân công ────────────────────────
    def action_ai_phan_cong(self):
        self.ensure_one()
        da        = self.du_an_id
        thong_tin = self._lay_thong_tin_du_an()
        yeu_cau   = self.yeu_cau_pc or "Đề xuất phân công công việc phù hợp với chức vụ của từng thành viên"

        # Danh sách tên thành viên để AI dùng đúng
        ds_thanh_vien = ', '.join(nv.ho_va_ten for nv in da.thanh_vien_ids)

        prompt = f"""Bạn là chuyên gia quản lý dự án. Hãy đề xuất phân công công việc dựa trên dữ liệu sau:

{thong_tin}

=== YÊU CẦU PHÂN CÔNG ===
{yeu_cau}

QUAN TRỌNG:
- Chỉ gán công việc cho các thành viên này (dùng đúng tên): {ds_thanh_vien}
- Tạo tối đa {max(len(da.thanh_vien_ids) * 2, 4)} công việc
- Trả về ĐÚNG định dạng JSON sau, KHÔNG thêm markdown hay text nào khác:

{{"cong_viec": [
  {{
    "ten": "Tên công việc cụ thể",
    "phu_trach": "Tên đúng như danh sách thành viên",
    "loai": "khoi_dong hoặc phat_trien hoặc kiem_thu hoặc trien_khai hoặc bao_cao",
    "uu_tien": "thap hoặc trung hoặc cao hoặc khan",
    "mo_ta": "Mô tả ngắn 1 câu"
  }}
]}}"""

        raw = self._goi_gemini_api(prompt)

        # Parse JSON từ response
        import re
        try:
            # Tìm JSON trong response (Gemini đôi khi bọc trong ```json```)
            json_match = re.search(r'\{[\s\S]*\}', raw)
            if not json_match:
                raise ValueError("Không tìm thấy JSON")
            data = json.loads(json_match.group())
            ds_cv = data.get('cong_viec', [])
        except Exception:
            # Hiển thị raw nếu parse lỗi
            self.ket_qua_pc = (
                '<div style="padding:12px;background:#fff3cd;border-radius:6px;">'
                '<b>AI trả lời (raw):</b><br/>'
                + raw.replace('\n', '<br/>')
                + '</div>'
            )
            return self._reopen()

        # Tạo mapping tên thành viên → object
        nhan_vien_map = {}
        for nv in da.thanh_vien_ids:
            nhan_vien_map[nv.ho_va_ten.lower()] = nv
            # Thêm các cách viết khác (tên ngắn)
            parts = nv.ho_va_ten.lower().split()
            if parts:
                nhan_vien_map[parts[-1]] = nv  # chỉ tên

        CongViec   = self.env.get('cong_viec')
        LOAI_VALID = {'khoi_dong', 'phat_trien', 'kiem_thu', 'trien_khai', 'bao_cao', 'khac'}
        UU_VALID   = {'thap', 'trung', 'cao', 'khan'}

        html  = '<div style="font-family:Arial;padding:14px;">'
        html += '<b style="color:#2c5f8a;font-size:14px;">🤖 Gemini AI đề xuất phân công:</b><br/><br/>'

        created = 0
        for i, item in enumerate(ds_cv, 1):
            ten   = item.get('ten', f'Công việc {i}')
            pt    = item.get('phu_trach', '').lower()
            loai  = item.get('loai', 'khac')
            uu    = item.get('uu_tien', 'trung')
            mo_ta = item.get('mo_ta', '')

            # Tìm nhân viên khớp tên
            nv_obj = None
            for key, nv in nhan_vien_map.items():
                if key in pt or pt in key:
                    nv_obj = nv
                    break
            # Fallback: gán xoay vòng
            if not nv_obj and da.thanh_vien_ids:
                nv_obj = da.thanh_vien_ids[(i - 1) % len(da.thanh_vien_ids)]

            # Tạo công việc trong Odoo
            tao_ok = False
            if CongViec and nv_obj:
                try:
                    CongViec.create({
                        'ten_cong_viec'     : ten,
                        'mo_ta'             : f'<p><i>Đề xuất bởi Gemini AI:</i> {mo_ta}</p>',
                        'du_an_id'          : da.id,
                        'nguoi_phu_trach_id': nv_obj.id,
                        'loai_cv'           : loai if loai in LOAI_VALID else 'khac',
                        'do_uu_tien'        : uu   if uu   in UU_VALID   else 'trung',
                        'ngay_bat_dau'      : da.ngay_bat_dau,
                        'deadline'          : da.ngay_ket_thuc,
                        'trang_thai'        : 'chua_bat_dau',
                    })
                    tao_ok  = True
                    created += 1
                except Exception:
                    tao_ok = False

            status_icon  = '✅' if tao_ok else '⚠️'
            status_label = 'Đã tạo' if tao_ok else 'Bỏ qua'
            ten_pt       = nv_obj.ho_va_ten if nv_obj else item.get('phu_trach', '?')

            html += (
                f'<div style="margin:6px 0;padding:10px;background:#f0f7ff;'
                f'border-radius:6px;border-left:3px solid #4a90d9;">'
                f'<b>{i}. {ten}</b> &nbsp; {status_icon} {status_label}<br/>'
                f'👤 {ten_pt} &nbsp;|&nbsp; 📂 {loai} &nbsp;|&nbsp; ⚡ {uu}<br/>'
                f'<small style="color:#666;">{mo_ta}</small>'
                f'</div>'
            )

        html += (
            f'<br/><div style="padding:8px;background:#d4edda;border-radius:6px;">'
            f'<b>✅ Tổng cộng: {created}/{len(ds_cv)} công việc đã được tạo trong hệ thống.</b>'
            f'</div></div>'
        )

        self.ket_qua_pc = html
        self.da_tao_cv  = created > 0

        self.du_an_id.message_post(
            body=f"🤖 <b>Gemini AI đã phân tích và tạo {created} công việc</b> cho dự án."
        )

        return self._reopen()

    def action_luu_api_key(self):
        """Lưu Gemini API key vào system parameters để dùng lại."""
        if self.api_key:
            self.env['ir.config_parameter'].sudo().set_param('gemini.api_key', self.api_key)

    def _reopen(self):
        return {
            'type'     : 'ir.actions.act_window',
            'res_model': self._name,
            'res_id'   : self.id,
            'view_mode': 'form',
            'target'   : 'new',
        }
