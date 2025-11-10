from django.contrib import admin
from .models import PaperAccount, PaperPosition, PaperTransaction

# Register your models here.
admin.site.register(PaperAccount)
admin.site.register(PaperPosition)
admin.site.register(PaperTransaction)
