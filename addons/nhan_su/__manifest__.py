# -*- coding: utf-8 -*-
{
    'name': "Quản lý Nhân sự (HRM)",
    'summary': "Module nền: quản lý nhân viên, phòng ban, chức vụ cho hệ thống ERP",
    'description': """
        Module HRM – Quản lý Nhân sự
        ==============================
        - Quản lý hồ sơ nhân viên (CRUD đầy đủ)
        - Quản lý đơn vị / phòng ban
        - Quản lý chức vụ
        - Lịch sử công tác
        - Chứng chỉ / bằng cấp
        - Trạng thái làm việc
        - Dữ liệu nhân viên là nguồn gốc cho các module Dự án và Công việc
    """,
    'author': "FIT-DNU – Nhóm BTL",
    'category': 'Human Resources',
    'version': '1.0',
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/demo_data.xml',
        'views/don_vi_views.xml',
        'views/chuc_vu_views.xml',
        'views/nhan_vien_views.xml',
        'views/lich_su_cong_tac_views.xml',
        'views/chung_chi_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
