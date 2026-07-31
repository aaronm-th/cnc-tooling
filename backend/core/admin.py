from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from . import models as md
from django.utils.html import format_html

from django import forms
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path
from datetime import datetime

from .csv_import import parse_legacy_csv


class TimeImportForm(forms.Form):
    csv_file = forms.FileField(label="CSV-Datei")

class WorkingTimeHistoryInline(admin.TabularInline):
    model = md.WorkingTimeHistory
    extra = 1

class EmployeeAdminForm(forms.ModelForm):
    # Wir definieren explizite Felder für das UI
    mo = forms.FloatField(label="Montag", min_value=0, max_value=24)
    di = forms.FloatField(label="Dienstag", min_value=0, max_value=24)
    mi = forms.FloatField(label="Mittwoch", min_value=0, max_value=24)
    do = forms.FloatField(label="Donnerstag", min_value=0, max_value=24)
    fr = forms.FloatField(label="Freitag", min_value=0, max_value=24)
    sa = forms.FloatField(label="Samstag", min_value=0, max_value=0) # Standard 0
    so = forms.FloatField(label="Sonntag", min_value=0, max_value=0)

    class Meta:
        model = md.Employee
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Falls ein Objekt existiert, Werte aus dem JSON in die Felder laden
        if self.instance and self.instance.work_days_schema:
            schema = self.instance.work_days_schema
            days = ['mo', 'di', 'mi', 'do', 'fr', 'sa', 'so']
            for i, day in enumerate(days):
                self.fields[day].initial = schema.get(str(i), 0)

    def save(self, commit=True):
        employee = super().save(commit=False)
        
        # 1. Werte aus den Formularfeldern einsammeln
        days = ['mo', 'di', 'mi', 'do', 'fr', 'sa', 'so']
        new_schema = {str(i): self.cleaned_data[day] for i, day in enumerate(days)}
        
        if commit:
            employee.save()
            
            # 2. Historien-Eintrag für HEUTE holen oder erstellen
            today = timezone.localdate()
            
            # Verhindert zirkuläre Imports, falls nötig
            from attendance.models import WorkingTimeHistory 
            
            history, created = WorkingTimeHistory.objects.get_or_create(
                employee=employee,
                valid_from=today,
                defaults={'work_days_schema': new_schema}
            )
            
            # Wenn der Eintrag bereits existierte, aktualisieren wir das Schema
            if not created:
                history.work_days_schema = new_schema
                history.save()
                
        return employee


@admin.register(md.Employee)
class EmployeeAdmin(UserAdmin):
    form = EmployeeAdminForm
    list_display = ('id','first_name', 'last_name', 'work_days_schema', 'phone', 'photo')
    search_fields = ('first_name', 'last_name')
    ordering = ('last_name',)
    inlines = [WorkingTimeHistoryInline]

    fieldsets = (
            (None, {'fields': ('username', 'password', 'chip_id')}),
            ('Persönliche Informationen', {'fields': ('first_name', 'last_name', 'email', 'phone', 'photo', 'joined_at')}), # Hier 'phone' und 'photo' hinzugefügt
            ('Berechtigungen', {
                'fields': ('is_active', 'is_staff', 'is_superuser', 'user_permissions'),
            }),
            ('Zusatzinformationen', {'fields': ('last_login', 'date_joined', 'vacation_days_per_year')}),
            ('Arbeitszeiten (Soll)', {'fields': ('mo', 'di', 'mi', 'do', 'fr', 'sa', 'so')}),

        )

    change_form_template = "core/employee_change_form.html"

    def display_groups(self, obj):
        return ", ".join([group.name for group in obj.groups.all()])
    
    display_groups.short_description = 'Groups'

    def get_urls(self):
        custom_urls = [
            path(
                "<int:employee_id>/import-times/",
                self.admin_site.admin_view(self.import_times_view),
                name="core_employee_import_times",
            ),
        ]
        return custom_urls + super().get_urls()

    def import_times_view(self, request, employee_id):
        from attendance.models import WorkDay, WorkSession

        employee = get_object_or_404(md.Employee, pk=employee_id)

        if request.method == "POST":
            form = TimeImportForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    days = parse_legacy_csv(form.cleaned_data["csv_file"].file)
                except ValueError as e:
                    messages.error(request, f"CSV konnte nicht gelesen werden: {e}")
                    return redirect("admin:core_employee_import_times", employee_id=employee.id)

                imported, skipped = 0, []

                for day_date, pairs in days:
                    work_day, _ = WorkDay.objects.get_or_create(
                        employee=employee, date=day_date,
                        defaults={"day_type": WorkDay.DayType.WORK},
                    )
                    for t_in, t_out in pairs:
                        if t_out is None:
                            skipped.append(
                                f"{day_date} {t_in}: kein Check-Out vorhanden – übersprungen."
                            )
                            continue
                        check_in = timezone.make_aware(datetime.combine(day_date, t_in))
                        check_out = timezone.make_aware(datetime.combine(day_date, t_out))
                        try:
                            WorkSession(work_day=work_day, check_in=check_in, check_out=check_out).save()
                            imported += 1
                        except Exception as e:
                            skipped.append(f"{day_date} {t_in}–{t_out}: {e}")

                messages.success(request, f"{imported} Zeiterfassungen importiert für {employee.name}.")
                if skipped:
                    messages.warning(request, "Übersprungen:\n" + "\n".join(skipped))
                return redirect("admin:core_employee_change", employee.id)
        else:
            form = TimeImportForm()

        return render(
            request,
            "core/employee_import_times.html",
            {"form": form, "employee": employee, "opts": self.model._meta},
        )

    def get_form(self, request, obj=None, **kwargs):
        """
        Diese Methode holt das Formular (egal ob für Erstellung oder Bearbeitung)
        und zwingt das E-Mail-Feld dazu, NICHT mehr verpflichtend zu sein.
        """
        form = super().get_form(request, obj, **kwargs)
        if 'email' in form.base_fields:
            form.base_fields['email'].required = False
        return form

@admin.register(md.WorkingTimeHistory)
class WorkingTimeHistoryAdmin(admin.ModelAdmin):
    list_display = ('employee', 'valid_from', 'work_days_schema')
    list_filter = ('employee', 'valid_from')
    search_fields = ('employee__first_name', 'employee__last_name')
    ordering = ('-valid_from',)


@admin.register(md.VacationQuota)
class VacationQuotaAdmin(admin.ModelAdmin):
    list_display = ('employee', 'year', 'total_days', 'carried_over')
    list_filter = ('employee', 'year')
    search_fields = ('employee__first_name', 'employee__last_name', 'year')
    ordering = ('employee__last_name', 'year')
 

@admin.register(md.Scratchpad)
class EmployeeScratchpadAdmin(admin.ModelAdmin):
    # Zeige die formatierte Vorschau in der Detailansicht an
    fields = ('employee', 'formatted_content', 'updated_at')
    
    # Das originale 'content' blenden wir aus und machen die Vorschau read-only
    readonly_fields = ('formatted_content', 'updated_at')
    
    # Steuert die Tabellen-Übersicht
    list_display = ('employee', 'formatted_content', 'updated_at')

    def formatted_content(self, obj):
        # format_html erlaubt Django, das HTML im Browser zu rendern
        return format_html(obj.content) if obj.content else "-"
    
    # Gibt der Spalte im Admin einen schönen Namen
    formatted_content.short_description = "Inhalt (Formatiert)"

@admin.register(md.TodoItem)
class TodoItemAdmin(admin.ModelAdmin):
    list_display = ('employee', 'text', 'completed', 'created_at')
    list_filter = ('employee', 'completed', 'created_at')
    search_fields = ('employee__first_name', 'employee__last_name', 'text')
    ordering = ('-created_at',)


@admin.register(md.Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'title', 'notification_type', 'read', 'created_at', 'link_to')
    list_filter = ('recipient', 'notification_type', 'read', 'created_at', 'link_to')
    search_fields = ('recipient__first_name', 'recipient__last_name', 'title', 'message')
    ordering = ('-created_at',)