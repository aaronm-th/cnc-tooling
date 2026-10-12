from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from . import models as md
from django.utils.html import format_html

from django import forms
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path
from datetime import datetime




class EmployeeAdminForm(forms.ModelForm):

    class Meta:
        model = md.Employee
        fields = '__all__'


@admin.register(md.Employee)
class EmployeeAdmin(UserAdmin):
    form = EmployeeAdminForm
    list_display = ('id','first_name', 'last_name', 'phone')
    search_fields = ('first_name', 'last_name')
    ordering = ('last_name',)

    