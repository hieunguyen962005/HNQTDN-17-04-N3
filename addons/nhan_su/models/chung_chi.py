from odoo import models, fields


class ChungChiBangCap(models.Model):
    _name = 'chung_chi_bang_cap'
    _description = 'Danh mục chứng chỉ / bằng cấp'
    _rec_name = 'ten_chung_chi'

    ma_chung_chi   = fields.Char("Mã chứng chỉ",            required=True)
    ten_chung_chi  = fields.Char("Tên chứng chỉ / Bằng cấp", required=True)
    mo_ta          = fields.Text("Mô tả")


class DanhSachChungChiBangCap(models.Model):
    _name = 'danh_sach_chung_chi_bang_cap'
    _description = 'Chứng chỉ bằng cấp của nhân viên'

    nhan_vien_id          = fields.Many2one('nhan_vien',          string="Nhân viên",    required=True, ondelete='cascade')
    chung_chi_bang_cap_id = fields.Many2one('chung_chi_bang_cap', string="Chứng chỉ",    required=True)
    ngay_cap      = fields.Date("Ngày cấp")
    noi_cap       = fields.Char("Nơi cấp")
    ngay_het_han  = fields.Date("Ngày hết hạn")
    ghi_chu       = fields.Text("Ghi chú")
