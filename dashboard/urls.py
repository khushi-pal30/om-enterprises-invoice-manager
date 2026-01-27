
from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import (
    clients_page,
    dashboard_view,
    pay_retention,
    mark_invoice_paid,
    send_invoice,
    add_project,
    add_invoice,
    add_client,
    edit_client,
    delete_client,
    view_reports,
    export_data,
    invoice_preview,
    download_invoice_pdf,
    project_edit,
    project_delete,
    projects,
    invoices,
    settings,
    edit_invoice,
    delete_invoice,
    project_detail,
    verify_tds,
    global_search,
    make_payment,
    payment_receipt,
    payment_history,
)

urlpatterns = [
    path('', dashboard_view, name='dashboard'),

    path('send_invoice/<int:invoice_id>/', send_invoice, name='send_invoice'),
    path('invoice/paid/<int:invoice_id>/', mark_invoice_paid, name='mark_paid'),

    path('add-project/', add_project, name='add_project'),
    path('projects/', projects, name='projects'),
    path('projects/edit/<int:project_id>/', project_edit, name='project_edit'),
    path('projects/delete/<int:project_id>/', project_delete, name='project_delete'),

    path('invoices/', invoices, name='invoices'),
    path('invoices/add/', add_invoice, name='add_invoice'),
    path('invoices/edit/<int:invoice_id>/', edit_invoice, name='edit_invoice'),
    path('invoices/delete/<int:invoice_id>/', delete_invoice, name='delete_invoice'),
    path('invoices/pay-retention/<int:invoice_id>/', pay_retention, name='pay_retention'),
    path('invoices/make_payment/<int:invoice_id>/', make_payment, name='make_payment'),
    path('invoices/payment_receipt/<int:invoice_id>/', payment_receipt, name='payment_receipt'),
    path('invoices/payment_history/<int:invoice_id>/', payment_history, name='payment_history'),
    path('invoice/preview/<int:invoice_id>/', invoice_preview, name='invoice_preview'),
    path('invoice/pdf/<int:invoice_id>/', download_invoice_pdf, name='invoice_pdf'),

    path('reports/', view_reports, name='view_reports'),
    path('export/', export_data, name='export_data'),

    path('clients/', clients_page, name='clients'),
    path('clients/add/', add_client, name='add_client'),
    path('clients/edit/<int:client_id>/', edit_client, name='edit_client'),
    path('clients/delete/<int:client_id>/', delete_client, name='delete_client'),
    path('settings/', settings, name='settings'),

    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('projects/<int:pk>/', project_detail, name='project_detail'),
    path('verify-tds/<int:invoice_id>/', verify_tds, name='verify_tds'),
    path('search/', global_search, name='global_search'),
]

