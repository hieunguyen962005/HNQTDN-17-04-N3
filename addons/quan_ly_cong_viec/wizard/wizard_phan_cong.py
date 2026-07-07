from odoo import models, fields, api
from odoo.exceptions import UserError


class WizardPhanCongCongViec(models.TransientModel):
    """
    Wizard: Phân công công việc hàng loạt cho nhiều nhân viên cùng lúc.
    Người dùng chọn dự án → chọn danh sách nhân viên → nhập thông tin chung
    → hệ thống tạo công việc cho từng người.
    """
    _name = 'wizard.phan_cong_cong_viec'
    _description = 'Phân công công việc hàng loạt'

    du_an_id = fields.Many2one(
        'du_an', string="Dự án",
        required=True,
        domain=[('trang_thai', 'in', ['dang_trien_khai', 'tam_dung'])]
    )
    ten_cong_viec = fields.Char("Tên công việc", required=True)
    mo_ta         = fields.Text("Mô tả chi tiết")
    loai_cv       = fields.Selection([
        ('khoi_dong',  'Khởi động'),
        ('phat_trien', 'Phát triển'),
        ('kiem_thu',   'Kiểm thử'),
        ('trien_khai', 'Triển khai'),
        ('bao_cao',    'Báo cáo'),
        ('khac',       'Khác'),
    ], string="Loại công việc", default='phat_trien', required=True)
    do_uu_tien    = fields.Selection([
        ('thap',  'Thấp'),
        ('trung', 'Trung bình'),
        ('cao',   'Cao'),
        ('khan',  'Khẩn cấp'),
    ], string="Độ ưu tiên", default='trung', required=True)
    ngay_bat_dau  = fields.Date("Ngày bắt đầu")
    deadline      = fields.Date("Deadline")
    nhan_vien_ids = fields.Many2many(
        'nhan_vien',
        string="Danh sách nhân viên phụ trách",
        domain="[('trang_thai','=','dang_lam'), ('id','in', thanh_vien_du_an_ids)]"
    )
    thanh_vien_du_an_ids = fields.Many2many(
        'nhan_vien', 'wizard_phan_cong_du_an_rel',
        string="Thành viên dự án",
        compute="_compute_thanh_vien_du_an"
    )

    @api.depends('du_an_id')
    def _compute_thanh_vien_du_an(self):
        for r in self:
            r.thanh_vien_du_an_ids = r.du_an_id.thanh_vien_ids if r.du_an_id else []

    @api.onchange('du_an_id')
    def _onchange_du_an(self):
        if self.du_an_id:
            self.ngay_bat_dau = self.du_an_id.ngay_bat_dau
            self.deadline     = self.du_an_id.ngay_ket_thuc
            self.nhan_vien_ids = self.du_an_id.thanh_vien_ids
        else:
            self.nhan_vien_ids = False

    def action_phan_cong(self):
        """Tạo công việc cho từng nhân viên được chọn."""
        self.ensure_one()
        if not self.nhan_vien_ids:
            raise UserError("Vui lòng chọn ít nhất một nhân viên để phân công!")
        if self.deadline and self.ngay_bat_dau and self.deadline < self.ngay_bat_dau:
            raise UserError("Deadline không thể nhỏ hơn ngày bắt đầu!")

        CongViec = self.env['cong_viec']
        created = CongViec
        for nv in self.nhan_vien_ids:
            cv = CongViec.create({
                'ten_cong_viec'     : '%s – %s' % (self.ten_cong_viec, nv.ho_va_ten),
                'mo_ta'             : self.mo_ta or '',
                'du_an_id'          : self.du_an_id.id,
                'nguoi_phu_trach_id': nv.id,
                'loai_cv'           : self.loai_cv,
                'do_uu_tien'        : self.do_uu_tien,
                'ngay_bat_dau'      : self.ngay_bat_dau,
                'deadline'          : self.deadline,
                'trang_thai'        : 'chua_bat_dau',
            })
            created |= cv

        # Ghi log vào dự án
        self.du_an_id.message_post(
            body="📋 Đã phân công <b>%d công việc</b> mới qua Wizard Phân công hàng loạt.<br/>"
                 "Tên công việc: <b>%s</b><br/>"
                 "Nhân viên: %s" % (
                     len(created),
                     self.ten_cong_viec,
                     ', '.join(self.nhan_vien_ids.mapped('ho_va_ten'))
                 )
        )

        # Mở danh sách công việc vừa tạo
        return {
            'type'      : 'ir.actions.act_window',
            'name'      : 'Công việc vừa phân công',
            'res_model' : 'cong_viec',
            'view_mode' : 'tree,form',
            'domain'    : [('id', 'in', created.ids)],
            'target'    : 'current',
        }
