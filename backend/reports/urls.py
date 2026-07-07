from django.urls import path
from . import views

urlpatterns = [
    # --- Dokumenten-Verwaltung ---
    path('api/documents/', views.EmployeeDocumentListView.as_view(), name='employee-document-list'),
    path('api/documents/upload/<int:employee_id>/', views.EmployeeDocumentUploadView.as_view(), name='employee-document-upload'),
    path('api/documents/download/<int:document_id>/', views.EmployeeDocumentDownloadView.as_view(), name='employee-document-download'),
    path('api/documents/delete/<int:document_id>/', views.EmployeeDocumentDeleteView.as_view(), name='employee-document-delete'),

    # --- Zeitnachweis-Berichte ---
    # 1. Die Dashboard-Tabelle für den Supervisor (Liste aller aktiven Mitarbeiter mit Ist/Soll)
    path('api/reports/admin/overview/', views.AdminMonthlyReportOverviewView.as_view(), name='admin-monthly-report-overview'),
    
    # 2. Der universelle Detail-Endpunkt (Liefert die Rohdaten für das jspdf-Schreibmaschinen-PDF)
    #    - Mitarbeiter ruft ihn ohne Parameter auf -> sieht eigene Daten
    #    - Admin ruft ihn mit ?employee_id=X auf -> sieht Daten von Mitarbeiter X
    path('api/reports/monthly-detail/', views.MonthlyReportDetailView.as_view(), name='monthly-report-detail'),
]