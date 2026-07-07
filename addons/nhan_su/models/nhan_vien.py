from odoo import models, fields, api
from datetime import date
from odoo.exceptions import ValidationError


class NhanVien(models.Model):
    _name = 'nhan_vien'
    _description = 'Hồ sơ nhân viên'
    _rec_name = 'ho_va_ten'
    _order = 'ho_va_ten asc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ── Định danh ──────────────────────────────────────────────────
    ma_dinh_danh = fields.Char("Mã nhân viên", required=True, copy=False, index=True, tracking=True)
    ho_ten_dem   = fields.Char("Họ tên đệm",   required=True, tracking=True)
    ten          = fields.Char("Tên",           required=True, tracking=True)
    ho_va_ten    = fields.Char("Họ và tên",     compute="_compute_ho_va_ten", store=True)

    # ── Cá nhân ────────────────────────────────────────────────────
    ngay_sinh    = fields.Date("Ngày sinh")
    tuoi         = fields.Integer("Tuổi", compute="_compute_tuoi", store=True)
    gioi_tinh    = fields.Selection([('nam','Nam'),('nu','Nữ'),('khac','Khác')],
                                    string="Giới tính", default='nam')
    que_quan     = fields.Char("Quê quán")
    dia_chi      = fields.Text("Địa chỉ hiện tại")
    email        = fields.Char("Email",         tracking=True)
    so_dien_thoai = fields.Char("Số điện thoại", tracking=True)
    anh          = fields.Binary("Ảnh đại diện", attachment=True)

    # ── Công việc ──────────────────────────────────────────────────
    don_vi_id    = fields.Many2one('don_vi',  string="Đơn vị / Phòng ban", ondelete='restrict', tracking=True)
    chuc_vu_id   = fields.Many2one('chuc_vu', string="Chức vụ hiện tại",   ondelete='restrict', tracking=True)
    ngay_vao_lam = fields.Date("Ngày vào làm", tracking=True)
    trang_thai   = fields.Selection([
        ('dang_lam',  'Đang làm việc'),
        ('tam_nghi',  'Tạm nghỉ'),
        ('nghi_viec', 'Đã nghỉ việc'),
    ], string="Trạng thái", default='dang_lam', required=True, tracking=True)

    # ── One2many ───────────────────────────────────────────────────
    lich_su_cong_tac_ids         = fields.One2many('lich_su_cong_tac',          'nhan_vien_id', string="Lịch sử công tác")
    danh_sach_chung_chi_bang_cap_ids = fields.One2many('danh_sach_chung_chi_bang_cap', 'nhan_vien_id', string="Chứng chỉ / Bằng cấp")

    # ── Thống kê (từ module khác) ──────────────────────────────────
    so_du_an_tham_gia   = fields.Integer("Dự án đang tham gia",   compute="_compute_so_du_an",   store=False)
    so_cong_viec_dang_lam = fields.Integer("Công việc đang làm", compute="_compute_so_cong_viec", store=False)

    _sql_constraints = [
        ('ma_dinh_danh_unique', 'UNIQUE(ma_dinh_danh)', 'Mã nhân viên phải là duy nhất!'),
    ]

    # ── Compute ────────────────────────────────────────────────────
    @api.depends('ho_ten_dem', 'ten')
    def _compute_ho_va_ten(self):
        for r in self:
            r.ho_va_ten = ' '.join(filter(None, [r.ho_ten_dem, r.ten]))

    @api.depends('ngay_sinh')
    def _compute_tuoi(self):
        today = date.today()
        for r in self:
            if r.ngay_sinh:
                r.tuoi = today.year - r.ngay_sinh.year - (
                    (today.month, today.day) < (r.ngay_sinh.month, r.ngay_sinh.day)
                )
            else:
                r.tuoi = 0

    def _compute_so_du_an(self):
        DuAn = self.env.get('du_an')
        for r in self:
            if DuAn is not None:
                r.so_du_an_tham_gia = DuAn.search_count([
                    ('thanh_vien_ids', 'in', r.id),
                    ('trang_thai', 'not in', ['hoan_thanh', 'huy'])
                ])
            else:
                r.so_du_an_tham_gia = 0

    def _compute_so_cong_viec(self):
        CongViec = self.env.get('cong_viec')
        for r in self:
            if CongViec is not None:
                r.so_cong_viec_dang_lam = CongViec.search_count([
                    ('nguoi_phu_trach_id', '=', r.id),
                    ('trang_thai', 'not in', ['hoan_thanh', 'huy'])
                ])
            else:
                r.so_cong_viec_dang_lam = 0

    # ── Onchange ───────────────────────────────────────────────────
    @api.onchange('ten', 'ho_ten_dem')
    def _onchange_ten_generate_ma(self):
        for r in self:
            if r.ho_ten_dem and r.ten and not r.ma_dinh_danh:
                initials = ''.join(w[0] for w in r.ho_ten_dem.lower().split() if w)
                r.ma_dinh_danh = (r.ten.lower().replace(' ', '') + initials)

    # ── Constraints ────────────────────────────────────────────────
    @api.constrains('tuoi')
    def _check_tuoi(self):
        for r in self:
            if r.tuoi and r.tuoi < 18:
                raise ValidationError("Tuổi nhân viên không được nhỏ hơn 18!")

    @api.constrains('ngay_vao_lam', 'ngay_sinh')
    def _check_ngay_vao_lam(self):
        for r in self:
            if r.ngay_vao_lam and r.ngay_sinh and r.ngay_vao_lam < r.ngay_sinh:
                raise ValidationError("Ngày vào làm không thể nhỏ hơn ngày sinh!")

    # ── Actions (smart buttons) ─────────────────────────────────────
    def action_xem_du_an(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Dự án của %s' % self.ho_va_ten,
            'res_model': 'du_an',
            'view_mode': 'tree,form',
            'domain': [('thanh_vien_ids', 'in', self.id)],
        }

    def action_xem_cong_viec(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Công việc của %s' % self.ho_va_ten,
            'res_model': 'cong_viec',
            'view_mode': 'tree,form',
            'domain': [('nguoi_phu_trach_id', '=', self.id)],
        }
