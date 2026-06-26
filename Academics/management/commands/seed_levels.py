"""
Management command to seed default UniversityLevel and SchoolLevel
records for every Organization (or a specific one).

Place this file at:
    <your_app>/management/commands/seed_levels.py

Usage:
    python manage.py seed_levels
    python manage.py seed_levels --org-id 3
    python manage.py seed_levels --org-id 3 --deactivate-missing
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from organization.models import Organization

# Adjust this import to wherever UniversityLevel / SchoolLevel actually live,
# e.g. `from education.models import UniversityLevel, SchoolLevel`
from Academics.models import UniversityLevel, SchoolLevel


class Command(BaseCommand):
    help = "Seed default UniversityLevel and SchoolLevel records for organizations."

    def add_arguments(self, parser):
        parser.add_argument(
            "--org-id",
            type=int,
            default=None,
            help="Only seed levels for this organization ID. Defaults to all organizations.",
        )
        parser.add_argument(
            "--deactivate-missing",
            action="store_true",
            help=(
                "Set is_active=False on any existing level rows for an org "
                "whose name is not in the seed list (instead of leaving them untouched)."
            ),
        )

    def handle(self, *args, **options):
        org_id = options["org_id"]
        deactivate_missing = options["deactivate_missing"]

        if org_id is not None:
            try:
                organizations = [Organization.objects.get(pk=org_id)]
            except Organization.DoesNotExist:
                raise CommandError(f"Organization with id={org_id} does not exist.")
        else:
            organizations = list(Organization.objects.all())

        if not organizations:
            self.stdout.write(self.style.WARNING("No organizations found. Nothing to seed."))
            return

        # Order here defines the `order` field value (1-indexed).
        university_order = [
            UniversityLevel.LevelChoices.DIPLOMA,
            UniversityLevel.LevelChoices.BACHELORS,
            UniversityLevel.LevelChoices.MASTERS,
            UniversityLevel.LevelChoices.PHD,
        ]

        school_order = [
            SchoolLevel.LevelChoices.PRE_SCHOOL,
            SchoolLevel.LevelChoices.PRE_PRIMARY,
            SchoolLevel.LevelChoices.PRIMARY,
            SchoolLevel.LevelChoices.LOWER_SECONDARY,
            SchoolLevel.LevelChoices.SECONDARY,
            SchoolLevel.LevelChoices.HIGHER_SECONDARY,
        ]

        total_created = 0
        total_updated = 0

        with transaction.atomic():
            for org in organizations:
                created, updated = self._seed_levels(
                    org=org,
                    model=UniversityLevel,
                    ordered_names=university_order,
                    deactivate_missing=deactivate_missing,
                )
                total_created += created
                total_updated += updated

                created, updated = self._seed_levels(
                    org=org,
                    model=SchoolLevel,
                    ordered_names=school_order,
                    deactivate_missing=deactivate_missing,
                )
                total_created += created
                total_updated += updated

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Created {total_created} level(s), updated {total_updated} level(s) "
                f"across {len(organizations)} organization(s)."
            )
        )

    def _seed_levels(self, org, model, ordered_names, deactivate_missing):
        """
        Create/update level rows for a given org+model, assigning `order`
        based on position in `ordered_names` (1-indexed).

        Avoids unique_together collisions on (org, order) by doing the
        update in two passes: first push everything to temporary high
        order values, then assign the final order values.
        """
        created_count = 0
        updated_count = 0

        existing = {obj.name: obj for obj in model.objects.filter(org=org)}

        # Pass 1: bump existing rows' order out of the way to avoid
        # unique_together("org", "order") collisions during reassignment.
        offset = 100000
        to_bump = [obj for obj in existing.values()]
        for i, obj in enumerate(to_bump):
            model.objects.filter(pk=obj.pk).update(order=offset + i)

        # Pass 2: create or update with correct order.
        seen_names = set()
        for index, name in enumerate(ordered_names, start=1):
            seen_names.add(name)
            obj = existing.get(name)
            if obj is None:
                model.objects.create(
                    org=org,
                    name=name,
                    order=index,
                    is_active=True,
                )
                created_count += 1
            else:
                if obj.order != index or not obj.is_active:
                    obj.order = index
                    obj.is_active = True
                    obj.save(update_fields=["order", "is_active"])
                else:
                    obj.order = index
                    obj.save(update_fields=["order"])
                updated_count += 1

        if deactivate_missing:
            stale_names = set(existing.keys()) - seen_names
            if stale_names:
                model.objects.filter(org=org, name__in=stale_names, is_active=True).update(
                    is_active=False
                )

        return created_count, updated_count