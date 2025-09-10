from __future__ import annotations

from typing import Any, Dict

from rest_framework import serializers


class CapabilityManifestSerializer(serializers.Serializer):
    agent_ids = serializers.ListField(
        child=serializers.CharField(), allow_empty=False
    )
    tool_ids = serializers.ListField(
        child=serializers.CharField(), allow_empty=True, required=False
    )
    memory_namespaces = serializers.ListField(
        child=serializers.CharField(), allow_empty=True, required=False
    )
    queue = serializers.ChoiceField(choices=["public", "sensitive"])  # route selection
    max_tokens = serializers.IntegerField(min_value=0)
    max_cost_cents = serializers.IntegerField(min_value=0)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)
    metadata = serializers.DictField(child=serializers.CharField(), required=False)

    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Additional policy checks can be applied here (RBAC, quotas, etc.)
        return data


