from django.contrib import admin
from . import models as md
from django.db import transaction
from datetime import timedelta

class WorkSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'employee', 'check_in', 'check_out')
    list_filter = ('work_day__employee', 'check_in')

    def employee(self, obj):
        return obj.work_day.employee
    employee.admin_order_field = 'work_day__employee'


admin.site.register(md.WorkSession, WorkSessionAdmin)


class ChangeRequestAdmin(admin.ModelAdmin):
    list_display = ('requested_by', 'old_check_in', 'old_check_out', 'requested_check_in', 'requested_check_out', 'duration_minutes', 'status', 'reviewed_by')
    list_filter = ('requested_by', 'reviewed_by', 'status')
    sorting = ('-created_at',)

    def duration_minutes(self, obj):
        
        dur_min = f"{obj.duration_difference / 60:.0f}"
        
        return f"+{dur_min}" if obj.duration_difference >= 0 else dur_min
    
admin.site.register(md.WSChangeRequest, ChangeRequestAdmin)




class WorkDayAdmin(admin.ModelAdmin):
    list_display = ('id', 'employee', 'date', 'get_total_hours', 'day_type')
    list_filter = ('employee', 'date', 'day_type')
    sorting = ('-date')

    def get_total_hours(self, obj):
        return f"{obj.total_hours:.2f}"
    get_total_hours.short_description = "Total Hours"



admin.site.register(md.WorkDay, WorkDayAdmin)


class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ('employee', 'leave_type', 'leave_start', 'leave_end', 'request_date')
    list_filter = ('employee', 'leave_type', 'leave_start', 'leave_end', 'request_date')

    actions = ['approve_leave_requests']

    @admin.action(description='Ausgewählte Anträge genehmigen & Tage generieren')
    def approve_leave_requests(self, request, queryset):
        created_total = 0
        
        # Wir nutzen eine Transaktion, damit alles oder nichts passiert
        with transaction.atomic():
            for leave in queryset:
                if leave.status == 'pending':
                    # 1. Status aktualisieren
                    leave.status = 'approved'
                    leave.save()

                    # 2. Tage generieren
                    curr = leave.leave_start
                    while curr <= leave.leave_end:
                        if curr.weekday() < 5:  # Nur Mo-Fr
                            wd, created = md.WorkDay.objects.get_or_create(
                                employee=leave.employee,
                                date=curr,
                                defaults={'day_type': leave.leave_type}
                            )
                            if created:
                                created_total += 1
                        curr += timedelta(days=1)
        
        self.message_user(request, f"Erfolgreich genehmigt. {created_total} Arbeitstage wurden im Kalender angelegt.")


admin.site.register(md.LeaveRequest, LeaveRequestAdmin)

