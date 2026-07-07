# -*- coding: utf-8 -*-
{
    'name': "Quản lý Dự án",
    'summary': "Quản lý dự án tích hợp HRM, Công việc và AI phân tích",
    'description': """
        Module Quản lý Dự án
        ======================
        - Tạo và quản lý dự án, chọn thành viên từ HRM
        - Workflow: Nháp → Đang triển khai → Hoàn thành / Huỷ
        - [MỨC 2] Xác nhận dự án → tự động tạo công việc cho thành viên
        - [MỨC 2] Tiến độ tự động cập nhật khi công việc hoàn thành
        - [MỨC 3] AI Chatbot phân tích dự án (Anthropic Claude)
        - [MỨC 3] AI tự động đề xuất & tạo phân công công việc
    """,
    'author': "FIT-DNU – Nhóm BTL",
    'category': 'Project Management',
    'version': '1.0',
    'depends': ['base', 'mail', 'nhan_su'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'data/demo_data.xml',
        'wizard/wizard_ai_du_an_views.xml',
        'views/du_an_views.xml',
        'views/bao_cao_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
