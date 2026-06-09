from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from users.models import CustomUser
from organization.models import Organization


class Command(BaseCommand):
    """
    Creates a sysadmin user for a specific organization.
    
    Usage:
        python manage.py create_sysadmin
    
    Runs interactively — prompts for all required fields.
    Only executable on the server directly, no HTTP endpoint exists.
    """

    # Shown when you run: python manage.py help create_sysadmin
    help = 'Creates a sysadmin user for a specific organization'

    def handle(self, *args, **options):
        """
        handle() is the entry point Django calls when the command runs.
        All your logic goes here.
        """
        self.stdout.write('\n--- Sysadmin Creation ---\n')

        # Step 1: Show available organizations and let operator pick one
        orgs = Organization.objects.all()

        if not orgs.exists():
            raise CommandError(
                'No organizations found. '
                'Create an organization first before creating a sysadmin.'
            )

        self.stdout.write('Available organizations:')
        for org in orgs:
            # self.stdout.write is used instead of print —
            # it respects Django's output management (can be silenced in tests)
            self.stdout.write(f'  [{org.id}] {org.name} — {org.domain_name}')

        while True:
            try:
                org_id = int(input('\nEnter organization ID: '))
                organization = Organization.objects.get(id=org_id)
                break
            except (ValueError, Organization.DoesNotExist):
                self.stdout.write(
                    self.style.ERROR('Invalid ID. Please try again.')
                )

        # Step 2: Collect user details
        while True:
            email = input('Email: ').strip()
            if not email:
                self.stdout.write(self.style.ERROR('Email cannot be empty.'))
                continue
            if CustomUser.objects.filter(email=email).exists():
                self.stdout.write(self.style.ERROR('A user with this email already exists.'))
                continue
            break

        username = input('Username (optional, press enter to skip): ').strip()

        # Step 3: Password with confirmation
        import getpass  # hides password input in terminal
        while True:
            password = getpass.getpass('Password: ')
            if len(password) < 8:
                self.stdout.write(self.style.ERROR('Password must be at least 8 characters.'))
                continue
            confirm = getpass.getpass('Confirm password: ')
            if password != confirm:
                self.stdout.write(self.style.ERROR('Passwords do not match. Try again.'))
                continue
            break

        # Step 4: Create the user inside a transaction —
        # if anything fails, nothing is saved to the DB
        # (no half-created users)
        try:
            with transaction.atomic():
                user = CustomUser.objects.create_user(
                    email=email,
                    password=password,
                    username=username,
                    org=organization,
                    is_sysadmin=True,
                    is_staff=True,      # staff so they can access Django admin if needed
                    is_active=True,
                    is_verified=True,   # sysadmin created by ops, no email verification needed
                )

            # style.SUCCESS prints in green in the terminal
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nSysadmin created successfully.'
                    f'\n  Email: {user.email}'
                    f'\n  Org:   {organization.name}'
                    f'\n  UUID:  {user.uuid}\n'
                )
            )

        except Exception as e:
            raise CommandError(f'Failed to create sysadmin: {str(e)}')