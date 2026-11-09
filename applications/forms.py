from pathlib import Path

from django import forms
from django.conf import settings

from jobmatch.form_styles import BootstrapMixin

from .models import Application


class ApplicationForm(BootstrapMixin, forms.Form):
    resume = forms.FileField(help_text="PDF, DOCX or TXT, up to 5 MB")
    cover_letter = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 4}))

    def clean_resume(self):
        f = self.cleaned_data["resume"]
        ext = Path(f.name).suffix.lower()
        if ext not in settings.RESUME_ALLOWED_EXTENSIONS:
            raise forms.ValidationError("Only PDF, DOCX or TXT files are accepted.")
        if f.size > settings.RESUME_MAX_BYTES:
            raise forms.ValidationError("The file is larger than 5 MB.")
        return f


class StatusForm(BootstrapMixin, forms.Form):
    status = forms.ChoiceField(choices=Application.Status.choices)
