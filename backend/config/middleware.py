# in deiner middleware.py
from django.http import HttpResponseForbidden

class RestrictAdminToTailscaleMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/admin/'):
            host = request.get_host() # Holt den Hostnamen (z.B. "100.115.80.90" oder "minipc.tailscale.net")
            
            # Prüfen, ob der Aufruf NICHT über Tailscale kam
            # (Entweder fängt die IP mit 100. an, oder sie enthält deinen Tailscale-Domainnamen)
            is_tailscale_ip = host.startswith('100.')
            is_tailscale_domain = '.ts.net' in host # MagicDNS von Tailscale
            
            if not (is_tailscale_ip or is_tailscale_domain):
                return HttpResponseForbidden("Admin-Zugriff nur via Tailscale erlaubt.")

        return self.get_response(request)