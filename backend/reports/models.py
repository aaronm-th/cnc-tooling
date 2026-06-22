import os
import uuid
from django.db import models
from django.conf import settings

def employee_document_upload_path(instance, filename):
    """
    Generiert einen sicheren, dynamischen Upload-Pfad:
    uploads/employee_docs/user_id/dokumententyp_uuid.ext
    """
    ext = filename.split('.')[-1]
    # UUID verhindert das Erraten von Dateinamen und Überschreiben bei gleichem Namen
    unique_filename = f"{instance.document_type}_{uuid.uuid4()}.{ext}"
    return os.path.join('employee_documents', str(instance.employee.id), unique_filename)

class EmployeeDocument(models.Model):
    # Definition der Typen, die exakt zu deinen Vue-Frontend-Optionen passen
    DOCUMENT_TYPE_CHOICES = [
        ('sozialversicherung', 'Sozialversicherungsnachweis'),
        ('arbeitsvertrag', 'Arbeitsvertrag'),
        ('ausweis', 'Ausweis / Identifikationsdokument'),
        ('bescheinigung', 'Ärztliche Bescheinigung'),
        ('sonstiges', 'Sonstiges'),
    ]

    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL, # Verweist sauber auf dein Employee (AbstractUser) Modell
        on_delete=models.CASCADE,
        related_name='documents'
    )
    document_type = models.CharField(
        max_length=30, 
        choices=DOCUMENT_TYPE_CHOICES,
        default='sonstiges'
    )
    file = models.FileField(
        upload_to=employee_document_upload_path,
        help_text="Erlaubte Formate: PDF, PNG, JPG"
    )
    original_filename = models.CharField(
        max_length=255, 
        help_text="Der ursprüngliche Name der Datei beim Upload"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_documents'
    )

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = "Mitarbeiter-Dokument"
        verbose_name = "Mitarbeiter-Dokumente"

    def __str__(self):
        return f"{self.get_document_type_display()} - {self.employee.name} ({self.uploaded_at.strftime('%d.%m.%Y')})"