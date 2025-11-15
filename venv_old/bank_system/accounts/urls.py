from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('bank/', views.deposit_withdraw_view, name='deposit_withdraw'),
    path('transfer/', views.transfer_view, name='transfer'),
    path('transactions/', views.transaction_history_view, name='transaction_history'),
    path('profile/', views.profile_view, name='profile'),
    path('transactions/pdf/', views.export_pdf_view, name='export_pdf'),
    path('export-pdf/', views.export_pdf_view, name='export_pdf'),
    path('receipt/<int:txn_id>/', views.download_receipt_html_pdf, name='generate_pdf'),
    path('', views.home_view, name='home'),








]
