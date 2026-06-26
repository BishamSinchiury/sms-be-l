from django.core.management.base import BaseCommand
from django.db import transaction

from organization.models import Organization
from Academics.models import Grade
from Academics.models.levels import SchoolLevel


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------
# Each entry maps a SchoolLevel.name value to the grades that belong to it.
# Adjust level names to match whatever your SchoolLevel seed data uses.
# ---------------------------------------------------------------------------

GRADE_SEED = [
    {
        "level": "pre_school",
        "grades": [
            {"name": Grade.GradeChoices.PRESCHOOL, "short": "PS",  "order": 1,  "duration": 12},
            {"name": Grade.GradeChoices.NURSERY,   "short": "NUR", "order": 2,  "duration": 12},
            {"name": Grade.GradeChoices.LKG,       "short": "LKG", "order": 3,  "duration": 12},
            {"name": Grade.GradeChoices.UKG,       "short": "UKG", "order": 4,  "duration": 12},
        ],
    },
    {
        "level": "primary",
        "grades": [
            {"name": Grade.GradeChoices.ONE,   "short": "G1",  "order": 5,  "duration": 12},
            {"name": Grade.GradeChoices.TWO,   "short": "G2",  "order": 6,  "duration": 12},
            {"name": Grade.GradeChoices.THREE, "short": "G3",  "order": 7,  "duration": 12},
            {"name": Grade.GradeChoices.FOUR,  "short": "G4",  "order": 8,  "duration": 12},
            {"name": Grade.GradeChoices.FIVE,  "short": "G5",  "order": 9,  "duration": 12},
        ],
    },
    {
        "level": "lower_secondary",
        "grades": [
            {"name": Grade.GradeChoices.SIX,   "short": "G6",  "order": 10, "duration": 12},
            {"name": Grade.GradeChoices.SEVEN, "short": "G7",  "order": 11, "duration": 12},
            {"name": Grade.GradeChoices.EIGHT, "short": "G8",  "order": 12, "duration": 12},
        ],
    },
    {
        "level": "secondary",
        "grades": [
            {"name": Grade.GradeChoices.NINE, "short": "G9",  "order": 13, "duration": 12},
            {"name": Grade.GradeChoices.TEN,  "short": "G10", "order": 14, "duration": 12},
        ],
    },
    {
        "level": "higher_secondary",
        "grades": [
            {"name": Grade.GradeChoices.ELEVEN, "short": "G11", "order": 15, "duration": 12},
            {"name": Grade.GradeChoices.TWELVE, "short": "G12", "order": 16, "duration": 12},
        ],
    },
]


class Command(BaseCommand):
    help = "Seed Grade records for all (or selected) organizations."

    def add_arguments(self, parser):
        parser.add_argument(
            "--org",
            dest="org_slug",
            default=None,
            help="Slug of a single organization to seed. Defaults to all organizations.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Print what would be created without writing to the database.",
        )

    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]
        org_slug: str | None = options["org_slug"]

        orgs = (
            Organization.objects.filter(slug=org_slug)
            if org_slug
            else Organization.objects.all()
        )

        if not orgs.exists():
            self.stderr.write(
                self.style.ERROR(
                    f"No organization found{f' with slug \"{org_slug}\"' if org_slug else ''}."
                )
            )
            return

        for org in orgs:
            self._seed_for_org(org, dry_run)

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry-run complete — nothing was saved."))
        else:
            self.stdout.write(self.style.SUCCESS("Grade seeding complete."))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _seed_for_org(self, org: "Organization", dry_run: bool) -> None:
        self.stdout.write(f"\nOrg: {org}")
        created_count = 0
        skipped_count = 0

        with transaction.atomic():
            for block in GRADE_SEED:
                level_name: str = block["level"]

                try:
                    level = SchoolLevel.objects.get(name=level_name, org=org)
                except SchoolLevel.DoesNotExist:
                    self.stderr.write(
                        self.style.WARNING(
                            f"  SchoolLevel '{level_name}' not found for org '{org}' — skipping its grades."
                        )
                    )
                    continue

                for g in block["grades"]:
                    exists = Grade.objects.filter(org=org, name=g["name"]).exists()

                    if exists:
                        self.stdout.write(f"  [skip]   {g['name']} already exists")
                        skipped_count += 1
                        continue

                    if dry_run:
                        self.stdout.write(
                            f"  [dry-run] would create {g['name']} "
                            f"(short={g['short']}, order={g['order']}, level={level_name})"
                        )
                        created_count += 1
                        continue

                    Grade.objects.create(
                        org=org,
                        level=level,
                        name=g["name"],
                        short=g["short"],
                        order=g["order"],
                        duration=g["duration"],
                        is_active=True,
                    )
                    self.stdout.write(
                        self.style.SUCCESS(f"  [create] {g['name']} → level: {level_name}")
                    )
                    created_count += 1

            if dry_run:
                # Roll back so nothing is persisted even if something slipped through.
                transaction.set_rollback(True)

        label = "would create" if dry_run else "created"
        self.stdout.write(
            f"  → {created_count} {label}, {skipped_count} skipped"
        )