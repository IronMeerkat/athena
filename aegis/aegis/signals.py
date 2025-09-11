from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.db import transaction
from typing import Optional, Set
from api.models import Doc
from api.tasks import embed_doc_task, delete_doc_task

EMBED_FIELDS: Set[str] = {"title", "text"}  # fields that require re-embedding

@receiver(post_save, sender=Doc)
def enqueue_embed_on_save(sender, instance: Doc, created: bool, update_fields: Optional[set], **kwargs):
    if not created and update_fields and EMBED_FIELDS.isdisjoint(update_fields):
        return  # no relevant change
    # run only after the DB commit succeeds
    transaction.on_commit(lambda: embed_doc_task.delay(str(instance.pk)))

@receiver(pre_delete, sender=Doc)
def enqueue_delete_on_delete(sender, instance: Doc, **kwargs):
    transaction.on_commit(lambda: delete_doc_task.delay(str(instance.pk)))
