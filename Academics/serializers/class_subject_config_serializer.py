from rest_framework import serializers
from Academics.models import ClassSubjectConfig, OptionalSubjectGroup, Grade, Stream, Subject


# ── OptionalSubjectGroup (Config-scoped) ──────────────────────────────────────

class ConfigOptionalGroupSerializer(serializers.ModelSerializer):
    subject_ids     = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False,
    )
    subjects_detail = serializers.SerializerMethodField(read_only=True)

    def get_subjects_detail(self, obj):
        return [{"id": s.id, "name": s.name, "code": s.code} for s in obj.subjects.all()]

    class Meta:
        model  = OptionalSubjectGroup
        fields = ["id", "name", "subject_ids", "subjects_detail", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value):
        return value.strip()

    def validate_subject_ids(self, value):
        if len(value) < 2:
            raise serializers.ValidationError(
                "An optional group must contain at least 2 subjects."
            )
        if len(value) != len(set(value)):
            raise serializers.ValidationError(
                "Duplicate subject IDs in the same group are not allowed."
            )
        return value

    def validate(self, attrs):
        config      = self.context.get("config") or getattr(self.instance, "config", None)
        name        = attrs.get("name") or getattr(self.instance, "name", None)
        subject_ids = attrs.get("subject_ids")

        if config is None:
            return attrs

        # unique name per config
        if name:
            qs = OptionalSubjectGroup.objects.filter(config=config, name=name)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"name": f"An optional group named '{name}' already exists for this config."}
                )

        # optional group capacity
        if config.total_optional_groups > 0 and not self.instance:
            current = OptionalSubjectGroup.objects.filter(config=config).count()
            if current >= config.total_optional_groups:
                raise serializers.ValidationError(
                    f"This config already has {current} optional group(s), "
                    f"which is the maximum allowed ({config.total_optional_groups})."
                )

        if subject_ids:
            org_id   = config.grade.org_id
            subjects = Subject.objects.filter(id__in=subject_ids)

            missing = set(subject_ids) - set(subjects.values_list("id", flat=True))
            if missing:
                raise serializers.ValidationError(
                    {"subject_ids": f"Subject ID(s) {sorted(missing)} not found."}
                )

            wrong_org = subjects.exclude(org_id=org_id)
            if wrong_org.exists():
                names = list(wrong_org.values_list("name", flat=True))
                raise serializers.ValidationError(
                    {"subject_ids": f"Subject(s) {names} do not belong to this organization."}
                )

            compulsory_ids = set(config.compulsory_subjects.values_list("id", flat=True))
            overlap = set(subject_ids) & compulsory_ids
            if overlap:
                names = list(Subject.objects.filter(id__in=overlap).values_list("name", flat=True))
                raise serializers.ValidationError(
                    {"subject_ids": f"Subject(s) {names} are already compulsory in this config."}
                )

            other_groups = OptionalSubjectGroup.objects.filter(config=config)
            if self.instance:
                other_groups = other_groups.exclude(pk=self.instance.pk)
            already_grouped = set(other_groups.values_list("subjects__id", flat=True))
            conflict = set(subject_ids) & already_grouped
            if conflict:
                names = list(Subject.objects.filter(id__in=conflict).values_list("name", flat=True))
                raise serializers.ValidationError(
                    {"subject_ids": f"Subject(s) {names} already belong to another optional group in this config."}
                )

        return attrs

    def _apply_subjects(self, instance, subject_ids):
        """Set the M2M subjects relation from a list of IDs."""
        if subject_ids is not None:
            instance.subjects.set(Subject.objects.filter(id__in=subject_ids))

    def create(self, validated_data):
        subject_ids = validated_data.pop("subject_ids", None)
        instance    = super().create(validated_data)
        self._apply_subjects(instance, subject_ids)
        return instance

    def update(self, instance, validated_data):
        subject_ids = validated_data.pop("subject_ids", None)
        instance    = super().update(instance, validated_data)
        self._apply_subjects(instance, subject_ids)
        return instance

    # Kept for backward compatibility — the view calls this after save().
    # Now redundant but harmless.
    def save_subjects(self, instance, subject_ids):
        self._apply_subjects(instance, subject_ids)


# ── ClassSubjectConfig ────────────────────────────────────────────────────────

class ClassSubjectConfigSerializer(serializers.ModelSerializer):
    grade_id   = serializers.IntegerField(source="grade.id")
    grade_name = serializers.SerializerMethodField(read_only=True)

    stream_ids     = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False, default=list,
    )
    compulsory_subject_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False, default=list,
    )

    streams_detail             = serializers.SerializerMethodField(read_only=True)
    compulsory_subjects_detail = serializers.SerializerMethodField(read_only=True)
    compulsory_count           = serializers.IntegerField(read_only=True)

    optional_groups      = ConfigOptionalGroupSerializer(many=True, read_only=True)
    optional_group_count = serializers.IntegerField(read_only=True)

    def get_grade_name(self, obj):
        return obj.grade.get_name_display() if obj.grade else None

    def get_streams_detail(self, obj):
        return [{"id": s.id, "name": s.name} for s in obj.streams.all()]

    def get_compulsory_subjects_detail(self, obj):
        return [{"id": s.id, "name": s.name, "code": s.code} for s in obj.compulsory_subjects.all()]

    class Meta:
        model  = ClassSubjectConfig
        fields = [
            "id",
            "grade_id",
            "grade_name",
            "stream_ids",
            "streams_detail",
            "total_compulsory_subjects",
            "compulsory_subject_ids",
            "compulsory_subjects_detail",
            "compulsory_count",
            "total_optional_groups",
            "optional_groups",
            "optional_group_count",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    # ── field-level ───────────────────────────────────────────────────────────

    def validate_total_compulsory_subjects(self, value):
        if value < 0:
            raise serializers.ValidationError("Must be 0 or a positive integer.")
        return value

    def validate_total_optional_groups(self, value):
        if value < 0:
            raise serializers.ValidationError("Must be 0 or a positive integer.")
        return value

    # ── object-level ─────────────────────────────────────────────────────────

    def validate(self, attrs):
        # resolve grade FK
        grade_data = attrs.pop("grade", None)
        grade_id   = grade_data.get("id") if isinstance(grade_data, dict) else None
        if grade_id is not None:
            try:
                attrs["grade"] = Grade.objects.get(id=grade_id)
            except Grade.DoesNotExist:
                raise serializers.ValidationError({"grade_id": "Grade not found."})

        grade = attrs.get("grade") or getattr(self.instance, "grade", None)
        if grade is None and not self.instance:
            raise serializers.ValidationError({"grade_id": "This field is required."})

        org_id = grade.org_id if grade else None

        total_compulsory = attrs.get(
            "total_compulsory_subjects",
            getattr(self.instance, "total_compulsory_subjects", 0),
        )
        total_optional = attrs.get(
            "total_optional_groups",
            getattr(self.instance, "total_optional_groups", 0),
        )

        # prevent lowering total_optional_groups below existing group count
        if self.instance and total_optional > 0:
            current_groups = self.instance.optional_groups.count()
            if current_groups > total_optional:
                raise serializers.ValidationError({
                    "total_optional_groups": (
                        f"This config already has {current_groups} optional group(s). "
                        f"You cannot set the maximum lower than that."
                    )
                })

        # prevent lowering total_compulsory_subjects below existing count
        if self.instance and total_compulsory > 0:
            existing = self.instance.compulsory_subjects.count()
            if existing > total_compulsory:
                raise serializers.ValidationError({
                    "total_compulsory_subjects": (
                        f"This config already has {existing} compulsory subject(s). "
                        f"You cannot set the maximum lower than that."
                    )
                })

        # validate stream_ids
        stream_ids = attrs.get("stream_ids", [])
        if stream_ids:
            streams = Stream.objects.filter(id__in=stream_ids)
            missing = set(stream_ids) - set(streams.values_list("id", flat=True))
            if missing:
                raise serializers.ValidationError(
                    {"stream_ids": f"Stream ID(s) {sorted(missing)} not found."}
                )
            wrong_org = streams.exclude(level__org_id=org_id)
            if wrong_org.exists():
                names = list(wrong_org.values_list("name", flat=True))
                raise serializers.ValidationError(
                    {"stream_ids": f"Stream(s) {names} do not belong to this organization."}
                )

        # validate compulsory_subject_ids
        compulsory_ids = attrs.get("compulsory_subject_ids", [])
        if compulsory_ids:
            if len(compulsory_ids) != len(set(compulsory_ids)):
                raise serializers.ValidationError(
                    {"compulsory_subject_ids": "Duplicate subject IDs are not allowed."}
                )

            if total_compulsory > 0 and len(compulsory_ids) > total_compulsory:
                raise serializers.ValidationError({
                    "compulsory_subject_ids": (
                        f"You are assigning {len(compulsory_ids)} compulsory subject(s), "
                        f"but this config allows a maximum of {total_compulsory}."
                    )
                })

            subjects = Subject.objects.filter(id__in=compulsory_ids)
            missing  = set(compulsory_ids) - set(subjects.values_list("id", flat=True))
            if missing:
                raise serializers.ValidationError(
                    {"compulsory_subject_ids": f"Subject ID(s) {sorted(missing)} not found."}
                )
            wrong_org = subjects.exclude(org_id=org_id)
            if wrong_org.exists():
                names = list(wrong_org.values_list("name", flat=True))
                raise serializers.ValidationError(
                    {"compulsory_subject_ids": f"Subject(s) {names} do not belong to this organization."}
                )

            # must not overlap with existing optional groups
            if self.instance:
                optional_ids = set(
                    OptionalSubjectGroup.objects
                    .filter(config=self.instance)
                    .values_list("subjects__id", flat=True)
                )
                overlap = set(compulsory_ids) & optional_ids
                if overlap:
                    names = list(Subject.objects.filter(id__in=overlap).values_list("name", flat=True))
                    raise serializers.ValidationError({
                        "compulsory_subject_ids": (
                            f"Subject(s) {names} already belong to an optional group in this config."
                        )
                    })

        return attrs

    def _save_m2m(self, instance, stream_ids, compulsory_ids):
        if stream_ids is not None:
            instance.streams.set(Stream.objects.filter(id__in=stream_ids))
        if compulsory_ids is not None:
            instance.compulsory_subjects.set(Subject.objects.filter(id__in=compulsory_ids))

    def create(self, validated_data):
        stream_ids     = validated_data.pop("stream_ids", [])
        compulsory_ids = validated_data.pop("compulsory_subject_ids", [])
        instance       = super().create(validated_data)
        self._save_m2m(instance, stream_ids, compulsory_ids)
        return instance

    def update(self, instance, validated_data):
        stream_ids     = validated_data.pop("stream_ids", None)
        compulsory_ids = validated_data.pop("compulsory_subject_ids", None)
        instance       = super().update(instance, validated_data)
        self._save_m2m(instance, stream_ids, compulsory_ids)
        return instance