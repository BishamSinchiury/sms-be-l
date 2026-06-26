import re
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from organization.models import Organization
from core.models import ContactDetail, AddressDetail, DocumentDetail

HEX_COLOR_RE = re.compile(r'^#[0-9A-Fa-f]{6}$')


def normalize_hex_color(value, field_name):
    value = value.strip()
    if not value.startswith('#'):
        value = f'#{value}'
    if not HEX_COLOR_RE.match(value):
        raise CommandError(
            f"--{field_name} must be a 6-digit hex color (e.g. #1A2B3C), got '{value}'"
        )
    return value


class Command(BaseCommand):
    help = "Create an Organization instance."

    def add_arguments(self, parser):
        parser.add_argument('--name', required=True, help='Organization name (unique)')
        parser.add_argument('--domain-name', required=True, help='Domain name (unique)')
        parser.add_argument('--address', required=True, help='Organization address')
        parser.add_argument('--motto', required=True, help='Organization motto')
        parser.add_argument('--primary-color', required=True, help='Primary color, e.g. #1A2B3C')
        parser.add_argument('--secondary-color', required=True, help='Secondary color, e.g. #FFFFFF')
        parser.add_argument('--logo', required=True, help='Path to logo image file')
        parser.add_argument('--cover-picture', required=True, help='Path to cover picture image file')

        # Optional related detail records — link existing ones by id, or
        # leave unset (the fields are nullable on Organization).
        parser.add_argument('--contact-id', type=int, default=None, help='Existing ContactDetail id to link')
        parser.add_argument('--address-detail-id', type=int, default=None, help='Existing AddressDetail id to link')
        parser.add_argument('--document-id', type=int, default=None, help='Existing DocumentDetail id to link')

    def handle(self, *args, **options):
        name = options['name'].strip()
        domain_name = options['domain_name'].strip()

        if Organization.objects.filter(name__iexact=name).exists():
            raise CommandError(f"An organization named '{name}' already exists.")
        if Organization.objects.filter(domain_name__iexact=domain_name).exists():
            raise CommandError(f"An organization with domain '{domain_name}' already exists.")

        primary_color = normalize_hex_color(options['primary_color'], 'primary-color')
        secondary_color = normalize_hex_color(options['secondary_color'], 'secondary-color')

        logo_path = Path(options['logo']).expanduser()
        cover_path = Path(options['cover_picture']).expanduser()
        if not logo_path.is_file():
            raise CommandError(f"Logo file not found: {logo_path}")
        if not cover_path.is_file():
            raise CommandError(f"Cover picture file not found: {cover_path}")

        contact = self._get_related(ContactDetail, options['contact_id'], 'ContactDetail')
        address_detail = self._get_related(AddressDetail, options['address_detail_id'], 'AddressDetail')
        document = self._get_related(DocumentDetail, options['document_id'], 'DocumentDetail')

        with transaction.atomic():
            org = Organization(
                name=name,
                address=options['address'].strip(),
                motto=options['motto'].strip(),
                primary_color=primary_color,
                secondary_color=secondary_color,
                domain_name=domain_name,
                contact=contact,
                address_detail=address_detail,
                document=document,
            )

            with logo_path.open('rb') as f:
                org.logo.save(logo_path.name, File(f), save=False)

            with cover_path.open('rb') as f:
                org.cover_picture.save(cover_path.name, File(f), save=False)

            org.save()

        self.stdout.write(self.style.SUCCESS(
            f"Created organization '{org.name}' (id={org.id}, domain={org.domain_name})"
        ))

    def _get_related(self, model, pk, label):
        if pk is None:
            return None
        try:
            return model.objects.get(pk=pk)
        except model.DoesNotExist:
            raise CommandError(f"{label} with id={pk} does not exist.")
        

"""
python manage.py create_organization \
  --name "EECOHM SCHool of Excellece" \
  --domain-name "localhost" \
  --address "Birtamode-1m Jhapa" \
  --motto "Learn Grow Innovate" \
  --primary-color "#1A2B3C" \
  --secondary-color "#FFFFFF" \
  --logo /home/bisham/Code/sms-no-ai/be/media/organizations/logo.png \
  --cover-picture /home/bisham/Code/sms-no-ai/be/media/organizations/485139512_1184580736788673_935997330072119496_n.jpg
"""