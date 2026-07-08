from odoo import models, fields, api


class DuAnInherit(models.Model):
    
    _inherit = 'du_an'

    cong_viec_ids = fields.One2many(
        'cong_viec', 'du_an_id', string="Công việc"
    )

    # Ghi đè lại compute tiến độ để dùng One2many thật (nhanh hơn search)
    tong_cong_viec    = fields.Integer("Tổng công việc",  compute="_compute_tien_do_v2", store=True)
    so_cv_hoan_thanh  = fields.Integer("Đã hoàn thành",  compute="_compute_tien_do_v2", store=True)
    so_cv_dang_lam    = fields.Integer("Đang thực hiện", compute="_compute_tien_do_v2", store=True)
    so_cv_qua_han     = fields.Integer("Quá hạn",        compute="_compute_tien_do_v2", store=True)
    tien_do_phan_tram = fields.Float("Tiến độ (%)",      compute="_compute_tien_do_v2", store=True)

    @api.depends('cong_viec_ids', 'cong_viec_ids.trang_thai', 'cong_viec_ids.la_qua_han')
    def _compute_tien_do_v2(self):
        for r in self:
            all_cv  = r.cong_viec_ids.filtered(lambda cv: cv.trang_thai != 'huy')
            done    = all_cv.filtered(lambda cv: cv.trang_thai == 'hoan_thanh')
            doing   = all_cv.filtered(lambda cv: cv.trang_thai == 'dang_thuc_hien')
            overdue = all_cv.filtered(lambda cv: cv.la_qua_han)
            r.tong_cong_viec    = len(all_cv)
            r.so_cv_hoan_thanh  = len(done)
            r.so_cv_dang_lam    = len(doing)
            r.so_cv_qua_han     = len(overdue)
            r.tien_do_phan_tram = (len(done) / len(all_cv) * 100) if all_cv else 0.0
