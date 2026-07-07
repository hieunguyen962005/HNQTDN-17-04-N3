from odoo import models, fields, api
from odoo.exceptions import ValidationError


class LichSuCongTac(models.Model):
    _name = 'lich_su_cong_tac'
    _description = 'Lịch sử công tác'
    _order = 'ngay_bat_dau desc'

    nhan_vien_id  = fields.Many2one('nhan_vien', string="Nhân viên", required=True, ondelete='cascade')
    chuc_vu_id    = fields.Many2one('chuc_vu',   string="Chức vụ")
    don_vi_id     = fields.Many2one('don_vi',    string="Đơn vị / Phòng ban")
    loai_chuc_vu  = fields.Selection([('chinh','Chính'),('kiem_nhiem','Kiêm nhiệm')],
                                     string="Loại chức vụ", default='chinh', required=True)
    ngay_bat_dau  = fields.Date("Ngày bắt đầu", required=True)
    ngay_ket_thuc = fields.Date("Ngày kết thúc")
    ghi_chu       = fields.Text("Ghi chú")

    @api.constrains('ngay_bat_dau', 'ngay_ket_thuc')
    def _check_dates(self):
        for r in self:
            if r.ngay_ket_thuc and r.ngay_bat_dau and r.ngay_ket_thuc < r.ngay_bat_dau:
                raise ValidationError("Ngày kết thúc không thể nhỏ hơn ngày bắt đầu!")
