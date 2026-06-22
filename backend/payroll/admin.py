from django.contrib import admin
from .models import Payroll

@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = ("employee", "period_start", "period_end", "total_hours", "total_salary")
    list_filter = ("period_start", "period_end")
    readonly_fields = ("total_hours", "overtime_hours", "total_salary")
