from django import forms
from .models import WSChangeRequest, WorkSession, LeaveRequest
from django.utils import timezone
from django.utils.timezone import localtime


class CreateRequestForm(forms.ModelForm):
    class Meta:
        model = WSChangeRequest
        fields = ['requested_check_in', 'requested_check_out']
        widgets = {
            'requested_check_in': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'requested_check_out': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        check_in = cleaned_data.get('requested_check_in')
        check_out = cleaned_data.get('requested_check_out')
    

        if check_in and check_out and self.worksession:
            if check_in >= check_out:
                raise forms.ValidationError("Check-in must be before check-out.")
            if check_out >= timezone.now():
                raise forms.ValidationError("Check-out cannot be in the future.")

            overlapping_sessions = WorkSession.objects.filter(
                work_day = self.worksession.work_day,
                check_out__gt=check_in,
                check_in__lt=check_out
            ).exclude(id=self.worksession.id)

            if overlapping_sessions.exists():
                raise forms.ValidationError("This work session overlaps with an existing one.")

        return cleaned_data


    def __init__(self, *args, **kwargs):
        worksession = kwargs.pop('worksession', None)
        initial = kwargs.get('initial', {}).copy()

        if worksession:
            # Convert datetime to local timezone (Germany)
            check_in_local = localtime(worksession.check_in)
            check_out_local = localtime(worksession.check_out)

            # Format to HTML datetime-local input format (YYYY-MM-DDTHH:MM)
            initial['requested_check_in'] = check_in_local.strftime('%Y-%m-%dT%H:%M')
            initial['requested_check_out'] = check_out_local.strftime('%Y-%m-%dT%H:%M')

        kwargs['initial'] = initial
        super().__init__(*args, **kwargs)
        self.worksession = worksession


class EditRequestForm(forms.ModelForm):
    class Meta:
        model = WSChangeRequest
        fields = ['requested_check_in', 'requested_check_out']
        widgets = {
            'requested_check_in': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'requested_check_out': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, worksession=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.worksession = worksession  # Store the worksession instance for validation

    def clean(self):
        cleaned_data = super().clean()
        check_in = cleaned_data.get('requested_check_in')
        check_out = cleaned_data.get('requested_check_out')

        if self.worksession and check_in and check_out:
            if check_in >= check_out:
                raise forms.ValidationError("Check-in must be before check-out.")
            if check_out >= timezone.now():
                raise forms.ValidationError("Check-out cannot be in the future.")
            # Query existing work sessions for overlaps (excluding the current request)
            overlapping_sessions = WorkSession.objects.filter(
                work_day = self.worksession.work_day,
                check_out__gt=check_in,
                check_in__lt=check_out
            ).exclude(id=self.worksession.id)

            # Exclude the current change request from validation
            if self.instance.pk:
                overlapping_sessions = overlapping_sessions.exclude(
                    id=self.instance.worksession.id
                )

            if overlapping_sessions.exists():
                raise forms.ValidationError("The requested times overlap with an existing work session.")

        return cleaned_data
    


class CreateLeaveForm(forms.ModelForm):

    class Meta:
        model = LeaveRequest
        fields = ["leave_type", "leave_start", "leave_end", "note"]
        widgets = {
            "leave_start": forms.DateInput(attrs={"type": "date"}),
            "leave_end": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, employee=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.employee = employee

    def clean(self):
        cleaned_data = super().clean()
        leave_start = cleaned_data.get("leave_start")
        leave_end = cleaned_data.get("leave_end")

        if not leave_start or not leave_end:
            return cleaned_data

        if leave_start > leave_end:
            raise forms.ValidationError(
                "Begin must be before or equal to end."
            )

        # Overlap-Check für UI
        if self.employee:
            overlaps = LeaveRequest.objects.filter(
                employee=self.employee,
                status__in=["pending", "approved"],
                leave_start__lte=leave_end,
                leave_end__gte=leave_start,
            )

            if overlaps.exists():
                raise forms.ValidationError(
                    "This leave request overlaps with an existing one."
                )

        return cleaned_data
