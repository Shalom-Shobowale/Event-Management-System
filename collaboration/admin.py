from django.contrib import admin
from .models import Task, Conversation, Message, EventMember, ActivityLog, EventFile, EventNote

admin.site.register(Task)
admin.site.register(Conversation)
admin.site.register(Message)
admin.site.register(EventMember)
admin.site.register(ActivityLog)
admin.site.register(EventFile)
admin.site.register(EventNote)
