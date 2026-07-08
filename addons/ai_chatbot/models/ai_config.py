from odoo import models, fields


class AIConfig(models.Model):
    
    _name = 'ai.config'
    _description = 'Cấu hình AI Chatbot'
    _rec_name = 'ten_cau_hinh'

    ten_cau_hinh = fields.Char("Tên cấu hình", default="Cấu hình mặc định")
    gemini_api_key = fields.Char(
        "Google Gemini API Key",
        help="Lấy miễn phí tại https://aistudio.google.com/apikey"
    )
    model_ai = fields.Selection([
    ('gemini-2.5-flash',      'Gemini 2.5 Flash (Nhanh, miễn phí)'),
    ('gemini-2.5-flash-lite', 'Gemini 2.5 Flash Lite (Nhẹ, giới hạn free cao)'),
    ('gemini-2.5-pro',        'Gemini 2.5 Pro (Mạnh hơn, giới hạn thấp)'),
    ], string="Model AI", default='gemini-2.5-flash')
    active = fields.Boolean("Đang dùng", default=True)
    ghi_chu = fields.Text("Ghi chú")
