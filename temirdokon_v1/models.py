from django.db import models

class BaseModel(models.Model):
    """
    Abstract base model that universally enforces full_clean() on every save.
    This guarantees that Django model validations run automatically and consistently 
    across the entire project without needing to call super().clean() manually everywhere.
    """
    yaratilgan_vaqt = models.DateTimeField(auto_now_add=True)
    yangilangan_vaqt = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
