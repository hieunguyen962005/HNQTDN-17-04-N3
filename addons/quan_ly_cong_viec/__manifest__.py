# -*- coding: utf-8 -*-
{
    'name': "Quản lý Công việc",
    'summary': "Quản lý task/công việc – tích hợp với HRM và Dự án",
    'description': """
        Module Quản lý Công việc
        =========================
        - Tạo và phân công công việc cho nhân viên (lấy từ HRM)
        - Gắn công việc vào dự án (lấy từ Quản lý Dự án)
        - Workflow: Chưa bắt đầu → Đang thực hiện → Chờ duyệt → Hoàn thành / Huỷ
        - [MỨC 2] Khi hoàn thành CV → tự động cập nhật tiến độ dự án cha
        - Wizard phân công công việc hàng loạt
        - Phát hiện công việc quá hạn qua cron job hàng ngày
        - Kanban board, view quá hạn, báo cáo pivot/graph
    """,
    'author': "FIT-DNU – Nhóm BTL",
    'category': 'Project Management',
    'version': '1.0',
    'depends': ['base', 'mail', 'nhan_su', 'quan_ly_du_an'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'data/ir_cron.xml',
        'data/demo_data.xml',
        'wizard/wizard_phan_cong_views.xml',
        'views/cong_viec_views.xml',
        'views/du_an_form_inherit.xml',
        'views/bao_cao_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
