from django import forms
from django.core.exceptions import ValidationError

from admin_panel.models import Report


# Category whitelist per target type.
# A vendor report doesn't offer "fake_event"; an event report doesn't
# offer "fake_vendor". Everything else is fair game for any target.
CATEGORY_BY_TARGET = {
    'vendor': [
        Report.Category.FAKE_VENDOR,
        Report.Category.SCAM,
        Report.Category.HARASSMENT,
        Report.Category.INAPPROPRIATE,
        Report.Category.OTHER,
    ],
    'event': [
        Report.Category.FAKE_EVENT,
        Report.Category.SCAM,
        Report.Category.HARASSMENT,
        Report.Category.INAPPROPRIATE,
        Report.Category.OTHER,
    ],
    'review': [
        Report.Category.HARASSMENT,
        Report.Category.INAPPROPRIATE,
        Report.Category.OTHER,
    ],
    'host': [
        Report.Category.HARASSMENT,
        Report.Category.SCAM,
        Report.Category.INAPPROPRIATE,
        Report.Category.OTHER,
    ],
    'message': [
        Report.Category.HARASSMENT,
        Report.Category.SCAM,
        Report.Category.INAPPROPRIATE,
        Report.Category.OTHER,
    ],
    'booking': [
        Report.Category.SCAM,
        Report.Category.HARASSMENT,
        Report.Category.INAPPROPRIATE,
        Report.Category.OTHER,
    ],
}

# Auto-priority per category. Keeps the admin queue pre-sorted.
PRIORITY_BY_CATEGORY = {
    Report.Category.SCAM:          Report.Priority.CRITICAL,
    Report.Category.HARASSMENT:    Report.Priority.HIGH,
    Report.Category.FAKE_VENDOR:   Report.Priority.HIGH,
    Report.Category.FAKE_EVENT:    Report.Priority.HIGH,
    Report.Category.INAPPROPRIATE: Report.Priority.MEDIUM,
    Report.Category.OTHER:         Report.Priority.LOW,
}

SUPPORTED_TARGETS = set(CATEGORY_BY_TARGET.keys())

MIN_DESCRIPTION_LENGTH = 30
MAX_DESCRIPTION_LENGTH = 2000


class ReportForm(forms.Form):
    """
    Form for creating a Report from the customer side.

    Not a ModelForm because we're going to build the Report instance
    explicitly in the view — we need to compute priority, validate the
    target against the DB, and enforce rate limits in the view, not in
    the form. The form handles input shape only.
    """
    target_type = forms.CharField(max_length=50)
    target_id = forms.CharField(max_length=100)
    target_label = forms.CharField(max_length=300, required=False)
    category = forms.ChoiceField(choices=Report.Category.choices)
    reason = forms.CharField(
        min_length=MIN_DESCRIPTION_LENGTH,
        max_length=MAX_DESCRIPTION_LENGTH,
        widget=forms.Textarea(attrs={'rows': 5}),
    )

    def clean_target_type(self):
        t = (self.cleaned_data.get('target_type') or '').strip().lower()
        if t not in SUPPORTED_TARGETS:
            raise ValidationError(f'Unsupported target type: {t}')
        return t

    def clean(self):
        cleaned = super().clean()
        target_type = cleaned.get('target_type')
        category = cleaned.get('category')

        # Category must be valid for the given target type
        if target_type and category:
            allowed = CATEGORY_BY_TARGET.get(target_type, [])
            if category not in allowed:
                raise ValidationError(
                    f'Category "{category}" is not valid for target type "{target_type}".'
                )

        # Collapse whitespace in the reason so "spam" filters can't be bypassed
        # with tab/newline tricks — and so the stored reason reads cleanly.
        reason = cleaned.get('reason')
        if reason:
            cleaned['reason'] = ' '.join(reason.split())

        return cleaned

    @staticmethod
    def priority_for(category):
        """Look up the auto-priority for a category."""
        return PRIORITY_BY_CATEGORY.get(category, Report.Priority.MEDIUM)

    @staticmethod
    def categories_for(target_type):
        """Return the list of valid Category values for a target type."""
        return CATEGORY_BY_TARGET.get(target_type, [])

    @staticmethod
    def labels_for(target_type):
        """Return [(value, label), ...] for the given target type."""
        allowed = CATEGORY_BY_TARGET.get(target_type, [])
        return [(c.value, c.label) for c in allowed]