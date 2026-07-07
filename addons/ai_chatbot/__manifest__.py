# -*- coding: utf-8 -*-
{
    'name': "🤖 AI Chatbot Toàn hệ thống",
    'summary': "Chatbot AI truy vấn dữ liệu HRM + Dự án + Công việc bằng Google Gemini",
    'description': """
        AI Chatbot – Trợ lý thông minh toàn hệ thống
        ===============================================
        [MỨC 3 – Tích hợp AI/External API]

        Sử dụng Google Gemini API (miễn phí) để trả lời câu hỏi
        về toàn bộ dữ liệu trong hệ thống ERP:

        - Nhân sự: danh sách nhân viên, phòng ban, trạng thái
        - Dự án  : tiến độ, thành viên, deadline, trạng thái
        - Công việc: quá hạn, phân công, khối lượng theo người

        Ví dụ câu hỏi:
        • "Dự án nào đang bị chậm tiến độ?"
        • "Nhân viên nào đang có nhiều việc quá hạn nhất?"
        • "Tóm tắt tình trạng toàn bộ dự án đang triển khai"
        • "Phòng CNTT có bao nhiêu người đang làm việc?"
    """,
    'author': "FIT-DNU – Nhóm BTL",
    'category': 'Tools',
    'version': '1.0',
    'depends': ['base', 'mail', 'nhan_su', 'quan_ly_du_an', 'quan_ly_cong_viec'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_config_data.xml',
        'views/chatbot_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
