from django.db import models
from pgvector.django import VectorField


class StoreKV(models.Model):
    prefix = models.TextField()
    key = models.TextField()
    value = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    ttl_minutes = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'graph"."store'
        unique_together = (('prefix', 'key'),)
        indexes = [
            models.Index(fields=['prefix'], name='store_prefix_idx'),
        ]


class StoreVector(models.Model):
    prefix = models.TextField()
    key = models.TextField()
    field_name = models.TextField()
    embedding = VectorField(dimensions=1536)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'graph"."store_vectors'
        unique_together = (('prefix', 'key', 'field_name'),)
        indexes = [
            models.Index(fields=['prefix'], name='store_vectors_prefix_idx'),
        ]


