from rest_framework import serializers
from Academics.models import Sem, OptionalSubjectGroup, Subject
from Academics.models.programs import Program


# ── OptionalSubjectGroup (Sem-scoped) ────────────────────────────────────────

class SemOptionalGroupSerializer(serializers.ModelSerializer):
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
        sem         = self.context.get("sem") or getattr(self.instance, "sem", None)
        name        = attrs.get("name") or getattr(self.instance, "name", None)
        subject_ids = attrs.get("subject_ids")

        if sem is None:
            return attrs

        # unique name per sem
        if name:
            qs = OptionalSubjectGroup.objects.filter(sem=sem, name=name)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"name": f"An optional group named '{name}' already exists for this semester."}
                )

        # optional group capacity
        if sem.total_optional_groups > 0 and not self.instance:
            current = OptionalSubjectGroup.objects.filter(sem=sem).count()
            if current >= sem.total_optional_groups:
                raise serializers.ValidationError(
                    f"This semester already has {current} optional group(s), "
                    f"which is the maximum allowed ({sem.total_optional_groups})."
                )

        if subject_ids:
            org_id   = sem.program.org_id
            subjects = Subject.objects.filter(id__in=subject_ids)

            # all IDs must exist
            missing = set(subject_ids) - set(subjects.values_list("id", flat=True))
            if missing:
                raise serializers.ValidationError(
                    {"subject_ids": f"Subject ID(s) {sorted(missing)} not found."}
                )

            # org check
            wrong_org = subjects.exclude(org_id=org_id)
            if wrong_org.exists():
                names = list(wrong_org.values_list("name", flat=True))
                raise serializers.ValidationError(
                    {"subject_ids": f"Subject(s) {names} do not belong to this organization."}
                )

            # must not be compulsory in this sem
            compulsory_ids = set(sem.compulsory_subjects.values_list("id", flat=True))
            overlap = set(subject_ids) & compulsory_ids
            if overlap:
                names = list(Subject.objects.filter(id__in=overlap).values_list("name", flat=True))
                raise serializers.ValidationError(
                    {"subject_ids": f"Subject(s) {names} are already compulsory in this semester."}
                )

            # must not appear in another group of the same sem
            other_groups = OptionalSubjectGroup.objects.filter(sem=sem)
            if self.instance:
                other_groups = other_groups.exclude(pk=self.instance.pk)
            already_grouped = set(other_groups.values_list("subjects__id", flat=True))
            conflict = set(subject_ids) & already_grouped
            if conflict:
                names = list(Subject.objects.filter(id__in=conflict).values_list("name", flat=True))
                raise serializers.ValidationError(
                    {"subject_ids": f"Subject(s) {names} already belong to another optional group in this semester."}
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
    # Now redundant because create/update handle it, but harmless.
    def save_subjects(self, instance, subject_ids):
        self._apply_subjects(instance, subject_ids)


# ── Sem ───────────────────────────────────────────────────────────────────────

class SemSerializer(serializers.ModelSerializer):
    program_name = serializers.CharField(source="program.name", read_only=True)
    program_id   = serializers.IntegerField(source="program.id")

    compulsory_subject_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False, default=list,
    )
    compulsory_subjects_detail = serializers.SerializerMethodField(read_only=True)
    compulsory_count           = serializers.IntegerField(read_only=True)

    optional_groups       = SemOptionalGroupSerializer(many=True, read_only=True)
    optional_group_count  = serializers.IntegerField(read_only=True)

    def get_compulsory_subjects_detail(self, obj):
        return [{"id": s.id, "name": s.name, "code": s.code} for s in obj.compulsory_subjects.all()]

    class Meta:
        model = Sem
        fields = [
            "id",
            "name",
            "program_id",
            "program_name",
            "duration",
            "order",
            "total_compulsory_subjects",
            "total_optional_groups",
            "compulsory_subject_ids",
            "compulsory_subjects_detail",
            "compulsory_count",
            "optional_groups",
            "optional_group_count",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    # ── field-level ───────────────────────────────────────────────────────────

    def validate_name(self, value):
        return value.strip()

    def validate_duration(self, value):
        if value < 1:
            raise serializers.ValidationError("Duration must be at least 1 month.")
        return value

    def validate_order(self, value):
        if value < 1:
            raise serializers.ValidationError("Order must be a positive integer.")
        return value

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
        # resolve program FK
        program_data = attrs.pop("program", None)
        program_id   = program_data.get("id") if isinstance(program_data, dict) else None
        if program_id is not None:
            try:
                attrs["program"] = Program.objects.get(id=program_id)
            except Program.DoesNotExist:
                raise serializers.ValidationError({"program_id": "Program not found."})

        program = attrs.get("program") or getattr(self.instance, "program", None)
        if program is None and not self.instance:
            raise serializers.ValidationError({"program_id": "This field is required."})

        name  = attrs.get("name")  or getattr(self.instance, "name",  None)
        order = attrs.get("order") or getattr(self.instance, "order", None)

        # unique (program, name)
        if program and name:
            qs = Sem.objects.filter(program=program, name=name)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"name": "A semester with this name already exists for this program."}
                )

        # unique (program, order)
        if program and order:
            qs = Sem.objects.filter(program=program, order=order)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"order": "A semester with this order already exists for this program."}
                )

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
                        f"This semester already has {current_groups} optional group(s). "
                        f"You cannot set the maximum lower than that."
                    )
                })

        compulsory_ids = attrs.get("compulsory_subject_ids", [])

        # capacity check
        if total_compulsory > 0 and compulsory_ids:
            if len(compulsory_ids) > total_compulsory:
                raise serializers.ValidationError({
                    "compulsory_subject_ids": (
                        f"You are assigning {len(compulsory_ids)} compulsory subject(s), "
                        f"but this semester allows a maximum of {total_compulsory}."
                    )
                })

        # also check against already-assigned when patching capacity down
        if self.instance and total_compulsory > 0 and not compulsory_ids:
            existing = self.instance.compulsory_subjects.count()
            if existing > total_compulsory:
                raise serializers.ValidationError({
                    "total_compulsory_subjects": (
                        f"This semester already has {existing} compulsory subject(s). "
                        f"You cannot set the maximum lower than that."
                    )
                })

        if compulsory_ids:
            self._validate_subject_ids(
                ids=compulsory_ids,
                org_id=program.org_id if program else None,
                field_key="compulsory_subject_ids",
                sem=self.instance,
            )

        return attrs

    def _validate_subject_ids(self, ids, org_id, field_key, sem=None):
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError(
                {field_key: "Duplicate subject IDs are not allowed."}
            )
        subjects = Subject.objects.filter(id__in=ids)
        missing  = set(ids) - set(subjects.values_list("id", flat=True))
        if missing:
            raise serializers.ValidationError(
                {field_key: f"Subject ID(s) {sorted(missing)} not found."}
            )
        if org_id:
            wrong = subjects.exclude(org_id=org_id)
            if wrong.exists():
                names = list(wrong.values_list("name", flat=True))
                raise serializers.ValidationError(
                    {field_key: f"Subject(s) {names} do not belong to this organization."}
                )
        # must not appear in any optional group of the same sem
        if sem and sem.pk:
            optional_ids = set(
                OptionalSubjectGroup.objects
                .filter(sem=sem)
                .values_list("subjects__id", flat=True)
            )
            conflict = set(ids) & optional_ids
            if conflict:
                names = list(Subject.objects.filter(id__in=conflict).values_list("name", flat=True))
                raise serializers.ValidationError(
                    {field_key: f"Subject(s) {names} already belong to an optional group in this semester."}
                )

    def _save_m2m(self, instance, compulsory_ids):
        if compulsory_ids is not None:
            instance.compulsory_subjects.set(Subject.objects.filter(id__in=compulsory_ids))

    def create(self, validated_data):
        compulsory_ids = validated_data.pop("compulsory_subject_ids", [])
        instance       = super().create(validated_data)
        self._save_m2m(instance, compulsory_ids)
        return instance

    def update(self, instance, validated_data):
        compulsory_ids = validated_data.pop("compulsory_subject_ids", None)
        instance       = super().update(instance, validated_data)
        self._save_m2m(instance, compulsory_ids)
        return instance