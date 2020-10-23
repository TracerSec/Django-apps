from django.db import models

# Create your models here.
class todo(models.Model):
    title = models.CharField(max_length=100)
    complete=models.BooleanField(default=True)

    def __str__(self):
        return self.title