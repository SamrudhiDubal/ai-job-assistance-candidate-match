"""Adds Bootstrap CSS classes to every form widget."""
from django import forms


class BootstrapMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            w = field.widget
            if isinstance(w, forms.RadioSelect):
                w.attrs["class"] = "form-check-input"
            elif isinstance(w, forms.Select):
                w.attrs["class"] = "form-select"
            elif isinstance(w, forms.CheckboxInput):
                w.attrs["class"] = "form-check-input"
            else:
                w.attrs["class"] = "form-control"
