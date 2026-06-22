from django import template
from attendance.models import WSChangeRequest

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Safely fetches a dictionary item using a key."""
    return dictionary.get(key, "N/A")

@register.filter
def get_item2(queryset, worksession_id):
    try:
        return queryset.get(worksession_id=worksession_id)
    except WSChangeRequest.DoesNotExist:
        return None
    
