from django.contrib import admin
from .models import EmployeeDocument

@admin.register(EmployeeDocument)
class EmployeeDocumentAdmin(admin.ModelAdmin):
    list_display = ('employee', 'document_type', 'original_filename', 'uploaded_by')
    list_filter = ('employee', 'document_type', 'uploaded_by')
    search_fields = ('employee__first_name', 'employee__last_name', 'document_type', 'original_filename')
    ordering = ('employee__last_name', 'document_type')