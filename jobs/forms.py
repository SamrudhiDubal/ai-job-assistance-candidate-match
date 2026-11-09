from django import forms

from jobmatch.form_styles import BootstrapMixin

from .models import Job


class JobForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Job
        fields = ("title", "company", "location", "job_type", "experience_level",
                  "salary_min", "salary_max", "skills_required", "description")
        widgets = {"description": forms.Textarea(attrs={"rows": 8}),
                   "skills_required": forms.TextInput(attrs={"placeholder": "python, django, sql"})}
        labels = {"salary_min": "Minimum salary (per year)", "salary_max": "Maximum salary (per year)"}

    def clean(self):
        data = super().clean()
        lo, hi = data.get("salary_min"), data.get("salary_max")
        if lo and hi and lo > hi:
            self.add_error("salary_max", "Maximum salary must be at least the minimum.")
        return data


class JobSearchForm(BootstrapMixin, forms.Form):
    q = forms.CharField(required=False, label="Keyword")
    location = forms.CharField(required=False)
    job_type = forms.ChoiceField(required=False, choices=[("", "Any type")] + list(Job.JobType.choices))
    experience_level = forms.ChoiceField(required=False, choices=[("", "Any level")] + list(Job.Level.choices))
    skill = forms.CharField(required=False)
