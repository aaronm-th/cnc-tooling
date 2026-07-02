from django.urls import path
from . import views

urlpatterns = [
    path('api/work-sessions/', views.MonthlyWorkSessionListView.as_view(), name='work-sessions'),
    path('api/work-days/', views.MonthlyWorkDayListView.as_view(), name='monthly-work-days'),
    path('api/documents/', views.EmployeeDocumentListView.as_view(), name='employee-document-list'),
    path('api/documents/upload/<int:member_id>/', views.EmployeeDocumentUploadView.as_view(), name='employee-document-upload'),
    path('api/documents/download/<int:document_id>/', views.EmployeeDocumentDownloadView.as_view(), name='employee-document-download'),
    path('api/documents/delete/<int:document_id>/', views.EmployeeDocumentDeleteView.as_view(), name='employee-document-delete'),
]