
from django.contrib import admin
from .models import Client, Project, Invoice

admin.site.register(Client)
admin.site.register(Project)
admin.site.register(Invoice)
