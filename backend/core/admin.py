from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from . import models as md
from django.utils.html import format_html

from django import forms



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
        # Werte aus den Feldern zurück ins JSON konvertieren
        days = ['mo', 'di', 'mi', 'do', 'fr', 'sa', 'so']
        schema = {str(i): self.cleaned_data[day] for i, day in enumerate(days)}
        self.instance.work_days_schema = schema
        return super().save(commit=commit)


@admin.register(md.Employee)
class EmployeeAdmin(UserAdmin):
    form = EmployeeAdminForm
    list_display = ('id','first_name', 'last_name', 'work_days_schema', 'phone', 'photo')
    search_fields = ('first_name', 'last_name')
    ordering = ('last_name',)

    fieldsets = (
            (None, {'fields': ('username', 'password')}),
            ('Persönliche Informationen', {'fields': ('first_name', 'last_name', 'email', 'phone', 'photo', 'joined_at')}), # Hier 'phone' und 'photo' hinzugefügt
            ('Berechtigungen', {
                'fields': ('is_active', 'is_staff', 'is_superuser', 'user_permissions'),
            }),
            ('Zusatzinformationen', {'fields': ('last_login', 'date_joined', 'vacation_days_per_year')}),
            ('Arbeitszeiten (Soll)', {'fields': ('hours_per_day', 'mo', 'di', 'mi', 'do', 'fr', 'sa', 'so')}),

        )

    def display_groups(self, obj):
        return ", ".join([group.name for group in obj.groups.all()])
    
    display_groups.short_description = 'Groups'

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