from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class DuAn(models.Model):
    
    _name = 'du_an'
    _description = 'Dự án'
    _rec_name = 'ten_du_an'
    _order = 'ngay_bat_dau desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ── Thông tin cơ bản ───────────────────────────────────────────
    ma_du_an        = fields.Char("Mã dự án", required=True, copy=False, index=True, tracking=True)
    ten_du_an       = fields.Char("Tên dự án", required=True, tracking=True)
    mo_ta           = fields.Html("Mô tả / Mục tiêu")
    khach_hang      = fields.Char("Khách hàng / Đối tác")

    # ── Thời gian ──────────────────────────────────────────────────
    ngay_bat_dau     = fields.Date("Ngày bắt đầu",           required=True, tracking=True)
    ngay_ket_thuc    = fields.Date("Ngày kết thúc dự kiến",  required=True, tracking=True)
    ngay_hoan_thanh  = fields.Date("Ngày hoàn thành thực tế", readonly=True)

    # ── Nhân sự (lấy từ HRM) ──────────────────────────────────────
    truong_du_an_id = fields.Many2one(
        'nhan_vien', string="Trưởng dự án",
        domain=[('trang_thai', '=', 'dang_lam')],
        required=True, ondelete='restrict', tracking=True
    )
    thanh_vien_ids  = fields.Many2many(
        'nhan_vien', 'du_an_nhan_vien_rel', 'du_an_id', 'nhan_vien_id',
        string="Thành viên dự án",
        domain=[('trang_thai', '=', 'dang_lam')]
    )
    don_vi_chu_quan_id = fields.Many2one(
        'don_vi', string="Đơn vị chủ quản", ondelete='restrict'
    )
    so_thanh_vien = fields.Integer(
        "Số thành viên", compute="_compute_so_thanh_vien", store=True
    )

    # ── Workflow ───────────────────────────────────────────────────
    trang_thai = fields.Selection([
        ('nhap',            'Nháp'),
        ('dang_trien_khai', 'Đang triển khai'),
        ('tam_dung',        'Tạm dừng'),
        ('hoan_thanh',      'Hoàn thành'),
        ('huy',             'Huỷ bỏ'),
    ], string="Trạng thái", default='nhap', required=True, tracking=True)

    # ── Phân loại ─────────────────────────────────────────────────
    loai_du_an = fields.Selection([
        ('noi_bo',     'Nội bộ'),
        ('khach_hang', 'Khách hàng'),
        ('nghien_cuu', 'Nghiên cứu & Phát triển'),
    ], string="Loại dự án", default='noi_bo')
    do_uu_tien = fields.Selection([
        ('thap',  'Thấp'),
        ('trung', 'Trung bình'),
        ('cao',   'Cao'),
        ('khan',  'Khẩn cấp'),
    ], string="Độ ưu tiên", default='trung')
    ngan_sach = fields.Float("Ngân sách (VNĐ)", digits=(15, 0))
    ghi_chu   = fields.Text("Ghi chú")

    # ── Tiến độ: compute động, KHÔNG dùng One2many sang cong_viec ──
    # (tránh lỗi KeyError khi quan_ly_cong_viec chưa được cài)
    tong_cong_viec    = fields.Integer("Tổng công việc",   compute="_compute_tien_do", store=False)
    so_cv_hoan_thanh  = fields.Integer("Đã hoàn thành",   compute="_compute_tien_do", store=False)
    so_cv_dang_lam    = fields.Integer("Đang thực hiện",  compute="_compute_tien_do", store=False)
    so_cv_qua_han     = fields.Integer("Quá hạn",         compute="_compute_tien_do", store=False)
    tien_do_phan_tram = fields.Float("Tiến độ (%)",       compute="_compute_tien_do", store=False)

    _sql_constraints = [
        ('ma_du_an_unique', 'UNIQUE(ma_du_an)', 'Mã dự án phải là duy nhất!'),
    ]

    # ── Compute ────────────────────────────────────────────────────
    @api.depends('thanh_vien_ids')
    def _compute_so_thanh_vien(self):
        for r in self:
            r.so_thanh_vien = len(r.thanh_vien_ids)

    def _compute_tien_do(self):
        """
        Tính tiến độ từ model cong_viec nếu module đã được cài.
        Nếu chưa cài → trả về 0 để không gây lỗi.
        """
        CongViec = self.env.get('cong_viec')
        for r in self:
            if CongViec is None:
                r.tong_cong_viec    = 0
                r.so_cv_hoan_thanh  = 0
                r.so_cv_dang_lam    = 0
                r.so_cv_qua_han     = 0
                r.tien_do_phan_tram = 0.0
                continue
            all_cv  = CongViec.search([('du_an_id', '=', r.id), ('trang_thai', '!=', 'huy')])
            done    = all_cv.filtered(lambda cv: cv.trang_thai == 'hoan_thanh')
            doing   = all_cv.filtered(lambda cv: cv.trang_thai == 'dang_thuc_hien')
            overdue = all_cv.filtered(lambda cv: cv.la_qua_han)
            r.tong_cong_viec    = len(all_cv)
            r.so_cv_hoan_thanh  = len(done)
            r.so_cv_dang_lam    = len(doing)
            r.so_cv_qua_han     = len(overdue)
            r.tien_do_phan_tram = (len(done) / len(all_cv) * 100) if all_cv else 0.0

    # ── Onchange ───────────────────────────────────────────────────
    @api.onchange('truong_du_an_id')
    def _onchange_truong_du_an(self):
        if self.truong_du_an_id and self.truong_du_an_id not in self.thanh_vien_ids:
            self.thanh_vien_ids = [(4, self.truong_du_an_id.id)]

    # ── Constraints ────────────────────────────────────────────────
    @api.constrains('ngay_bat_dau', 'ngay_ket_thuc')
    def _check_dates(self):
        for r in self:
            if r.ngay_ket_thuc and r.ngay_bat_dau and r.ngay_ket_thuc < r.ngay_bat_dau:
                raise ValidationError("Ngày kết thúc không thể nhỏ hơn ngày bắt đầu!")

    # ── Workflow actions ───────────────────────────────────────────
    def action_xac_nhan(self):
        
        for r in self:
            if r.trang_thai != 'nhap':
                raise UserError("Chỉ xác nhận được dự án đang ở trạng thái Nháp!")
            if not r.thanh_vien_ids:
                raise UserError("Dự án phải có ít nhất một thành viên!")
            r.trang_thai = 'dang_trien_khai'
            count = r._tu_dong_tao_cong_viec()
            r.message_post(
                body="✅ Dự án xác nhận → <b>Đang triển khai</b>.<br/>"
                     "🤖 Tự động tạo <b>%d công việc khởi động</b> cho:<br/>%s" % (
                         count,
                         '<br/>'.join('• ' + nv.ho_va_ten for nv in r.thanh_vien_ids)
                     )
            )
        return True

    def action_tam_dung(self):
        for r in self:
            if r.trang_thai != 'dang_trien_khai':
                raise UserError("Chỉ tạm dừng được dự án đang triển khai!")
            r.trang_thai = 'tam_dung'
            r.message_post(body="⏸ Dự án đã tạm dừng.")

    def action_tiep_tuc(self):
        for r in self:
            if r.trang_thai != 'tam_dung':
                raise UserError("Dự án không đang tạm dừng!")
            r.trang_thai = 'dang_trien_khai'
            r.message_post(body="▶️ Dự án tiếp tục triển khai.")

    def action_hoan_thanh(self):
        for r in self:
            if r.trang_thai not in ('dang_trien_khai', 'tam_dung'):
                raise UserError("Không thể hoàn thành dự án ở trạng thái này!")
            r.trang_thai = 'hoan_thanh'
            r.ngay_hoan_thanh = fields.Date.today()
            r.message_post(body="🎉 Dự án hoàn thành ngày <b>%s</b>." % r.ngay_hoan_thanh)

    def action_huy(self):
        for r in self:
            if r.trang_thai == 'hoan_thanh':
                raise UserError("Không thể huỷ dự án đã hoàn thành!")
            r.trang_thai = 'huy'
            r.message_post(body="❌ Dự án đã bị huỷ.")

    def action_ve_nhap(self):
        for r in self:
            if r.trang_thai != 'huy':
                raise UserError("Chỉ đặt lại được dự án bị huỷ về Nháp!")
            r.trang_thai = 'nhap'
            r.message_post(body="🔄 Dự án về Nháp.")

    # ── Core: Tự động tạo công việc (Mức 2) ───────────────────────
    def _tu_dong_tao_cong_viec(self):
        
        CongViec = self.env.get('cong_viec')
        if CongViec is None:
            return 0
        count = 0
        for r in self:
            for nv in r.thanh_vien_ids:
                existing = CongViec.search([
                    ('du_an_id', '=', r.id),
                    ('nguoi_phu_trach_id', '=', nv.id),
                    ('loai_cv', '=', 'khoi_dong'),
                ], limit=1)
                if not existing:
                    CongViec.create({
                        'ten_cong_viec'     : '[Khởi động] %s – %s' % (r.ten_du_an, nv.ho_va_ten),
                        'mo_ta'             : '<p>Công việc tự động tạo khi xác nhận dự án <b>%s</b>.<br/>'
                                              'Phụ trách: <b>%s</b></p>' % (r.ten_du_an, nv.ho_va_ten),
                        'du_an_id'          : r.id,
                        'nguoi_phu_trach_id': nv.id,
                        'trang_thai'        : 'chua_bat_dau',
                        'do_uu_tien'        : r.do_uu_tien or 'trung',
                        'ngay_bat_dau'      : r.ngay_bat_dau,
                        'deadline'          : r.ngay_ket_thuc,
                        'loai_cv'           : 'khoi_dong',
                    })
                    count += 1
        return count

    # ── Smart buttons ──────────────────────────────────────────────
    def action_xem_cong_viec(self):
        return {
            'type'     : 'ir.actions.act_window',
            'name'     : 'Công việc – %s' % self.ten_du_an,
            'res_model': 'cong_viec',
            'view_mode': 'tree,form',
            'domain'   : [('du_an_id', '=', self.id)],
            'context'  : {'default_du_an_id': self.id},
        }

    def action_phan_cong_hang_loat(self):
        return {
            'type'     : 'ir.actions.act_window',
            'name'     : 'Phân công công việc hàng loạt',
            'res_model': 'wizard.phan_cong_cong_viec',
            'view_mode': 'form',
            'target'   : 'new',
            'context'  : {'default_du_an_id': self.id},
        }

    def action_mo_ai(self):
        """[MỨC 3] Mở wizard AI phân tích dự án."""
        return {
            'type'     : 'ir.actions.act_window',
            'name'     : '🤖 Trợ lý AI – %s' % self.ten_du_an,
            'res_model': 'wizard.ai_du_an',
            'view_mode': 'form',
            'target'   : 'new',
            'context'  : {'default_du_an_id': self.id},
        }
