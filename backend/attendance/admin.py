from django.contrib import admin, messages
from . import models as md
from django.db import transaction
from datetime import timedelta
from django.utils.timezone import localtime
from django.utils.html import format_html




class WorkSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'employee', 'check_in', 'check_out', 'is_auto_checkout')
    list_filter = ('work_day__employee', 'check_in')

    def employee(self, obj):
        return obj.work_day.employee
    employee.admin_order_field = 'work_day__employee'

admin.site.register(md.WorkSession, WorkSessionAdmin)



@admin.register(md.WSChangeRequest)
class WSChangeRequestAdmin(admin.ModelAdmin):
    # Spalten in der Übersicht
    list_display = (
        'requested_by', 
        'work_day', 
        'get_old_time', 
        'get_requested_time', 
        'get_duration_diff_display', 
        'status', 
        'request_date'
    )
    
    # Filter auf der rechten Seite
    list_filter = ('status', 'request_date', 'work_day__date')
    
    # Suchfelder
    search_fields = (
        'requested_by__first_name', 
        'requested_by__last_name', 
        'employee_note', 
        'admin_note'
    )
    
    # Detailseite Gruppierung
    fieldsets = (
        ('Metadaten', {
            'fields': ('status', 'requested_by', 'work_day', 'worksession')
        }),
        ('Alte Zeiten (System)', {
            'fields': ('old_check_in', 'old_check_out'),
            'description': 'Werden bei existierenden Sessions automatisch befüllt.'
        }),
        ('Beantragte Änderungen', {
            'fields': ('requested_check_in', 'requested_check_out', 'employee_note')
        }),
        ('Prüfung & Freigabe', {
            'fields': ('reviewed_by', 'reviewed_date', 'admin_note')
        }),
    )
    
    readonly_fields = ('request_date', 'old_check_in', 'old_check_out')
    
    # --- Custom Listen-Spalten (Formatierung) ---

    @admin.display(description='Alte Zeit')
    def get_old_time(self, obj):
        if obj.old_check_in and obj.old_check_out:
            old_in = localtime(obj.old_check_in).strftime('%H:%M')
            old_out = localtime(obj.old_check_out).strftime('%H:%M')
            return f"{old_in} - {old_out}"
        return "Neuanlage"

    @admin.display(description='Beantragt')
    def get_requested_time(self, obj):
        req_in = localtime(obj.requested_check_in).strftime('%H:%M')
        req_out = localtime(obj.requested_check_out).strftime('%H:%M')
        return f"{req_in} - {req_out}"

    @admin.display(description='Abweichung')
    def get_duration_diff_display(self, obj):
        diff = obj.duration_difference_minutes

        format_html('<span style="color: orange; font-weight: bold;">+{} Min.</span>', diff)

        if diff > 0:
            return format_html('<span style="color: orange; font-weight: bold;">+{} Min.</span>', diff)
        elif diff < 0:
            return format_html('<span style="color: orange; font-weight: bold;">{} Min.</span>', diff)
        return "0 Min."

    # --- Admin Actions (Massenbearbeitung) ---
    actions = ['approve_requests', 'reject_requests']

    @admin.action(description='Ausgewählte Anträge GENEHMIGEN')
    def approve_requests(self, request, queryset):
        success_count = 0
        for obj in queryset.filter(status='pending'):
            try:
                obj.approve(reviewer=request.user)
                success_count += 1
            except Exception as e:
                self.message_user(request, f"Fehler bei Antrag {obj.id}: {str(e)}", messages.ERROR)
        
        if success_count:
            self.message_user(request, f"{success_count} Anträge wurden erfolgreich genehmigt.", messages.SUCCESS)

    @admin.action(description='Ausgewählte Anträge ABLEHNEN')
    def reject_requests(self, request, queryset):
        # Hier wird eine Standardbegründung gesetzt, da Actions keinen Textinput im Standard haben
        updated = 0
        for obj in queryset.filter(status='pending'):
            obj.reject(reviewer=request.user, reason="Durch Administrator in Massenbearbeitung abgelehnt.")
            updated += 1
        
        if updated:
            self.message_user(request, f"{updated} Anträge wurden abgelehnt.", messages.WARNING)




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

