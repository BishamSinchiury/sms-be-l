# rbac/mixins.py
from rbac.models import ActivityLog
from rbac.utils import log_activity


class ActivityLoggingMixin:
    """
    Mix into any DRF view with perform_create/perform_update/perform_destroy
    hooks. No per-view Action enum entry needed — the verb is implied by
    which hook ran, and the entity comes from content_type automatically.

    Usage — usually zero config:
        class ProgramViewSet(ActivityLoggingMixin, ...):
            ...

    Opt out selectively if a view shouldn't log a particular verb:
        class ProgramViewSet(ActivityLoggingMixin, ...):
            log_skip = {"update"}   # don't log updates, only create/destroy

    Customize metadata captured on create/update:
        log_metadata_fields = ["name", "short", "level_id"]
    """
    log_skip = set()
    log_metadata_fields = None

    def _metadata_for(self, instance):
        fields = self.log_metadata_fields or []
        return {f: getattr(instance, f, None) for f in fields}

    def perform_create(self, serializer):
        instance = serializer.save()
        if "create" not in self.log_skip:
            log_activity(
                user=self.request.user,
                verb=ActivityLog.Verb.CREATED,
                request=self.request,
                target=instance,
                metadata=self._metadata_for(instance),
            )

    def perform_update(self, serializer):
        instance = serializer.save()
        if "update" not in self.log_skip:
            log_activity(
                user=self.request.user,
                verb=ActivityLog.Verb.UPDATED,
                request=self.request,
                target=instance,
                metadata={"fields": list(self.request.data.keys())},
            )

    def perform_destroy(self, instance):
        repr_, meta = str(instance), self._metadata_for(instance)
        super().perform_destroy(instance)
        if "destroy" not in self.log_skip:
            log_activity(
                user=self.request.user,
                verb=ActivityLog.Verb.DELETED,
                request=self.request,
                target=None,            # instance is gone, no FK to point at
                target_repr=repr_,
                metadata=meta,
            )