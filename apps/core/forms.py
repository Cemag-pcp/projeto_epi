from django import forms


class BootstrapModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            widget_class = widget.__class__.__name__
            if getattr(widget, "input_type", "") == "checkbox":
                css_class = "form-check-input"
            elif widget_class in {"Select", "SelectMultiple"}:
                css_class = "form-select"
            else:
                css_class = "form-control"
            existing = widget.attrs.get("class", "")
            widget.attrs["class"] = f"{existing} {css_class}".strip()