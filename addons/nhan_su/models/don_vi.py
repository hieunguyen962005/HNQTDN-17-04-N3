from odoo import models, fields, api


class DonVi(models.Model):
    _name = 'don_vi'
    _description = 'Đơn vị / Phòng ban'
    _rec_name = 'ten_don_vi'
    _order = 'ten_don_vi asc'

    ma_don_vi = fields.Char("Mã đơn vị", required=True, index=True)
    ten_don_vi = fields.Char("Tên đơn vị", required=True)
    mo_ta = fields.Text("Mô tả")
    truong_don_vi_id = fields.Many2one('nhan_vien', string="Trưởng đơn vị", ondelete='set null')
    nhan_vien_ids = fields.One2many('nhan_vien', 'don_vi_id', string="Nhân viên trong đơn vị")
    so_nhan_vien = fields.Integer("Số nhân viên đang làm", compute="_compute_so_nhan_vien", store=True)

    _sql_constraints = [
        ('ma_don_vi_unique', 'UNIQUE(ma_don_vi)', 'Mã đơn vị phải là duy nhất!'),
    ]

    @api.depends('nhan_vien_ids', 'nhan_vien_ids.trang_thai')
    def _compute_so_nhan_vien(self):
        for r in self:
            r.so_nhan_vien = len(r.nhan_vien_ids.filtered(lambda nv: nv.trang_thai == 'dang_lam'))
