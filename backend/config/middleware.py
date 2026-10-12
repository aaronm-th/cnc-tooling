from django.conf import settings
from django.http import HttpResponseForbidden

class RestrictAdminToTailscaleMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.DEBUG:
            return self.get_response(request)

        if request.path.startswith('/admin/'):
            host = request.get_host().lower() # .lower() verhindert Probleme bei Groß-/Kleinschreibung
            
            # 1. Erlaubte Hostnamen definieren
            is_tailscale_name = (host == 'stempelsystem' or '.ts.net' in host)
            is_tailscale_ip = host.startswith('100.')
            is_localhost = host.startswith('localhost') or host.startswith('127.0.0.1')
            
            # 2. Zugriff prüfen
            if not (is_tailscale_name or is_tailscale_ip or is_localhost):
                return HttpResponseForbidden("Admin-Zugriff nur via Tailscale erlaubt.")

        return self.get_response(request)