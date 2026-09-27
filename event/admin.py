from django.contrib import admin
from .models import Event

admin.site.register(Event)
from django.utils.html import format_html

from .models import Seat


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = (
        'label', 'event_link', 'section', 'status_badge',
        'guest_link', 'held_for_short', 'sort_order',
    )
    list_filter = ('status', 'section', 'event')
    search_fields = (
        'label', 'held_for',
        'event__name',
        'guest__full_name', 'guest__email',
    )
    readonly_fields = ('id', 'created_at', 'updated_at')
    list_per_page = 100
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Seat', {
            'fields': ('id', 'event', 'label', 'section', 'sort_order'),
        }),
        ('Status', {
            'fields': ('status', 'held_for', 'held_note'),
        }),
        ('Assignment', {
            'fields': ('guest',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
        }),
    )

    @admin.display(description='Event')
    def event_link(self, obj):
        return obj.event.name

    @admin.display(description='Guest')
    def guest_link(self, obj):
        if not obj.guest:
            return '—'
        return f'{obj.guest.full_name} ({obj.guest.email})'

    @admin.display(description='Held for')
    def held_for_short(self, obj):
        if not obj.held_for:
            return '—'
        return obj.held_for[:40] + ('…' if len(obj.held_for) > 40 else '')

    @admin.display(description='Status')
    def status_badge(self, obj):
        colors = {
            'available': '#c6f24e',  # lime
            'held':      '#7c5cff',  # violet
            'taken':     '#ff4800',  # flame
            'blocked':   '#71718a',  # ink
        }
        color = colors.get(obj.status, '#71718a')
        return format_html(
            '<span style="display:inline-block;padding:2px 8px;border-radius:9999px;'
            'background:{color}20;color:{color};border:1px solid {color}50;'
            'font-family:monospace;font-size:10px;text-transform:uppercase;'
            'letter-spacing:0.1em;">{label}</span>',
            color=color, label=obj.get_status_display()
        )