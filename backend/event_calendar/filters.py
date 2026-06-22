import django_filters
from django_filters import ChoiceFilter
from attendance.models import WSChangeRequest, LeaveRequest


class ChangeRequestFilter(django_filters.FilterSet):
    status = ChoiceFilter(field_name='status', choices=[('approved', 'Genehmigt'), ('rejected', 'Abgelehnt')])

    class Meta:
        model = WSChangeRequest
        fields = ['status']


class LeaveRequestFilter(django_filters.FilterSet):
    status = ChoiceFilter(field_name='status', choices=[('approved', 'Genehmigt'), ('rejected', 'Abgelehnt')])

    class Meta:
        model = LeaveRequest
        fields = ['status']



