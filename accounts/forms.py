from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from jobmatch.form_styles import BootstrapMixin

from .models import User


class RegisterForm(BootstrapMixin, UserCreationForm):
    # Administrators cannot register themselves; they are created by a command.
    role = forms.ChoiceField(
        choices=[(User.Role.CANDIDATE, "Candidate (looking for a job)"),
                 (User.Role.EMPLOYER, "Employer (hiring)")],
        widget=forms.RadioSelect,
        initial=User.Role.CANDIDATE,
    )

    class Meta:
        model = User
        fields = ("name", "email", "role", "company")
        help_texts = {"company": "Employers only"}

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        data = super().clean()
        if data.get("role") == User.Role.EMPLOYER and not data.get("company"):
            self.add_error("company", "Please enter your company name.")
        return data


class LoginForm(BootstrapMixin, AuthenticationForm):
    username = forms.EmailField(label="Email", widget=forms.EmailInput(attrs={"autofocus": True}))


class ProfileForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ("name", "title", "company", "skills", "bio")
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 4}),
            "skills": forms.TextInput(attrs={"placeholder": "python, django, sql"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.is_candidate:
            del self.fields["company"]
        else:
            del self.fields["skills"]
            del self.fields["title"]
