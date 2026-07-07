from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import date


class CongViec(models.Model):
    """
    Model Quản lý Công việc – điểm cuối trong luồng tự động hóa 3 module.

    LUỒNG NGHIỆP VỤ (Mức 2):
        HRM (nhan_vien) → DuAn (du_an) [XÁC NHẬN] → CongViec (cong_viec) [TỰ ĐỘNG TẠO]

    Khi công việc được HOÀN THÀNH:
        → Tự động cập nhật trường tien_do_phan_tram của dự án cha (via _compute_tien_do)
        → Ghi log vào chatter của cả công việc và dự án
    """
    _name = 'cong_viec'
    _description = 'Công việc'
    _rec_name = 'ten_cong_viec'
    _order = 'deadline asc, do_uu_tien desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ── Thông tin cơ bản ───────────────────────────────────────────
    ma_cong_viec    = fields.Char("Mã công việc",  copy=False, index=True,
                                  default=lambda self: self.env['ir.sequence'].next_by_code('cong_viec.seq') or '/')
    ten_cong_viec   = fields.Char("Tên công việc", required=True, tracking=True)
    mo_ta           = fields.Html("Mô tả chi tiết")
    loai_cv         = fields.Selection([
        ('khoi_dong',    'Khởi động'),
        ('phat_trien',   'Phát triển'),
        ('kiem_thu',     'Kiểm thử'),
        ('trien_khai',   'Triển khai'),
        ('bao_cao',      'Báo cáo'),
        ('khac',         'Khác'),
    ], string="Loại công việc", default='khac', required=True)

    # ── Liên kết module Dự án ──────────────────────────────────────
    du_an_id = fields.Many2one(
        'du_an', string="Thuộc dự án",
        ondelete='cascade', tracking=True, index=True
    )
    ten_du_an       = fields.Char("Tên dự án",     related='du_an_id.ten_du_an', store=True, readonly=True)
    trang_thai_du_an = fields.Selection(related='du_an_id.trang_thai', string="Trạng thái dự án", readonly=True)

    # ── Nhân sự (lấy từ HRM) ──────────────────────────────────────
    nguoi_phu_trach_id = fields.Many2one(
        'nhan_vien', string="Người phụ trách",
        domain=[('trang_thai', '=', 'dang_lam')],
        required=True, ondelete='restrict', tracking=True
    )
    nguoi_tao_id    = fields.Many2one(
        'nhan_vien', string="Người giao việc",
        domain=[('trang_thai', '=', 'dang_lam')],
        ondelete='restrict'
    )
    don_vi_id       = fields.Many2one(
        'don_vi', string="Đơn vị",
        related='nguoi_phu_trach_id.don_vi_id', store=True, readonly=True
    )

    # ── Thời gian ──────────────────────────────────────────────────
    ngay_bat_dau    = fields.Date("Ngày bắt đầu")
    deadline        = fields.Date("Deadline",         tracking=True)
    ngay_hoan_thanh = fields.Date("Ngày hoàn thành", readonly=True)
    la_qua_han      = fields.Boolean("Quá hạn?",      compute="_compute_qua_han", store=True)

    # ── Phân loại & Trạng thái ─────────────────────────────────────
    do_uu_tien      = fields.Selection([
        ('thap',  'Thấp'),
        ('trung', 'Trung bình'),
        ('cao',   'Cao'),
        ('khan',  'Khẩn cấp'),
    ], string="Độ ưu tiên", default='trung', tracking=True)
    trang_thai      = fields.Selection([
        ('chua_bat_dau',    'Chưa bắt đầu'),
        ('dang_thuc_hien',  'Đang thực hiện'),
        ('cho_duyet',       'Chờ duyệt'),
        ('hoan_thanh',      'Hoàn thành'),
        ('qua_han',         'Quá hạn'),
        ('huy',             'Huỷ'),
    ], string="Trạng thái", default='chua_bat_dau', required=True, tracking=True)

    # ── Ghi chú ────────────────────────────────────────────────────
    ket_qua         = fields.Text("Kết quả / Báo cáo hoàn thành")
    ghi_chu         = fields.Text("Ghi chú")

    # ── Compute ────────────────────────────────────────────────────
    @api.depends('deadline', 'trang_thai')
    def _compute_qua_han(self):
        today = date.today()
        for r in self:
            if r.deadline and r.trang_thai not in ('hoan_thanh', 'huy'):
                r.la_qua_han = r.deadline < today
            else:
                r.la_qua_han = False

    # ── Constraints ────────────────────────────────────────────────
    @api.constrains('ngay_bat_dau', 'deadline')
    def _check_dates(self):
        for r in self:
            if r.deadline and r.ngay_bat_dau and r.deadline < r.ngay_bat_dau:
                raise ValidationError("Deadline không thể nhỏ hơn ngày bắt đầu!")

    @api.constrains('nguoi_phu_trach_id', 'du_an_id')
    def _check_phu_trach_la_thanh_vien(self):
        """Người phụ trách phải là thành viên của dự án (nếu có gắn dự án)."""
        for r in self:
            if r.du_an_id and r.nguoi_phu_trach_id:
                if r.nguoi_phu_trach_id not in r.du_an_id.thanh_vien_ids:
                    raise ValidationError(
                        "Người phụ trách '%s' không phải thành viên của dự án '%s'!\n"
                        "Vui lòng thêm nhân viên này vào danh sách thành viên dự án trước."
                        % (r.nguoi_phu_trach_id.ho_va_ten, r.du_an_id.ten_du_an)
                    )

    # ── Workflow actions ───────────────────────────────────────────
    def action_bat_dau(self):
        for r in self:
            if r.trang_thai != 'chua_bat_dau':
                raise UserError("Công việc không ở trạng thái 'Chưa bắt đầu'!")
            r.trang_thai = 'dang_thuc_hien'
            if not r.ngay_bat_dau:
                r.ngay_bat_dau = date.today()
            r.message_post(body="🚀 Công việc đã bắt đầu thực hiện.")

    def action_nop_bao_cao(self):
        for r in self:
            if r.trang_thai != 'dang_thuc_hien':
                raise UserError("Chỉ có thể nộp báo cáo khi đang thực hiện!")
            r.trang_thai = 'cho_duyet'
            r.message_post(body="📋 Công việc đã nộp báo cáo, chờ phê duyệt.")

    def action_hoan_thanh(self):
        """
        [TỰ ĐỘNG HÓA MỨC 2] Khi hoàn thành công việc:
        - Cập nhật trạng thái → hoan_thanh
        - Ghi ngày hoàn thành
        - Trigger recompute tien_do_phan_tram trên dự án cha (qua cong_viec_ids → _compute_tien_do)
        - Ghi log vào chatter dự án
        """
        for r in self:
            if r.trang_thai not in ('dang_thuc_hien', 'cho_duyet', 'chua_bat_dau'):
                raise UserError("Không thể hoàn thành công việc ở trạng thái này!")
            r.trang_thai = 'hoan_thanh'
            r.ngay_hoan_thanh = date.today()
            r.la_qua_han = False
            r.message_post(
                body="✅ Công việc hoàn thành vào ngày <b>%s</b>." % r.ngay_hoan_thanh
            )
            # Ghi log vào dự án cha
            if r.du_an_id:
                r.du_an_id.message_post(
                    body="✅ Công việc <b>%s</b> (phụ trách: %s) đã hoàn thành.<br/>"
                         "Tiến độ dự án: <b>%.0f%%</b>" % (
                             r.ten_cong_viec,
                             r.nguoi_phu_trach_id.ho_va_ten,
                             r.du_an_id.tien_do_phan_tram
                         )
                )
                # Kiểm tra nếu tất cả công việc đều hoàn thành → gợi ý hoàn thành dự án
                all_done = all(
                    cv.trang_thai in ('hoan_thanh', 'huy')
                    for cv in r.du_an_id.cong_viec_ids
                )
                if all_done and r.du_an_id.trang_thai == 'dang_trien_khai':
                    r.du_an_id.message_post(
                        body="🎉 <b>Tất cả công việc đã hoàn thành!</b> "
                             "Bạn có thể bấm 'Hoàn thành' để đóng dự án."
                    )

    def action_huy(self):
        for r in self:
            if r.trang_thai == 'hoan_thanh':
                raise UserError("Không thể huỷ công việc đã hoàn thành!")
            r.trang_thai = 'huy'
            r.message_post(body="❌ Công việc đã bị huỷ.")

    def action_mo_lai(self):
        for r in self:
            if r.trang_thai not in ('huy', 'hoan_thanh'):
                raise UserError("Chỉ có thể mở lại công việc đã huỷ hoặc hoàn thành!")
            r.trang_thai = 'chua_bat_dau'
            r.ngay_hoan_thanh = False
            r.message_post(body="🔄 Công việc được mở lại.")

    # ── Scheduled action: phát hiện quá hạn ───────────────────────
    @api.model
    def _cap_nhat_qua_han(self):
        """
        Cron job: chạy hàng ngày, cập nhật trạng thái quá hạn.
        (Cấu hình trong data/ir_cron.xml nếu cần)
        """
        qua_han = self.search([
            ('trang_thai', 'in', ['chua_bat_dau', 'dang_thuc_hien']),
            ('deadline', '<', date.today().isoformat()),
        ])
        qua_han.write({'trang_thai': 'qua_han'})
        for cv in qua_han:
            cv.message_post(body="⚠️ Công việc đã quá hạn (deadline: %s)." % cv.deadline)
        return True
