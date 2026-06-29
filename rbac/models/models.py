import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from organization.models import Organization
from core.models import TimestampModel
from users.models import CustomUser
from django.core.exceptions import ValidationError



class Permission(TimestampModel):
    """
    A single action that can be allowed or denied.
    Scoped to an organization — each org manages its own permissions.
    
    codename is the machine-readable identifier used in code:
        "can_view_users", "can_delete_reports"
    name is the human-readable label shown in the dashboard:
        "Can view users", "Can delete reports"
    """
    uuid     = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    codename = models.CharField(max_length=100)
    name     = models.CharField(max_length=255)
    org      = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='permissions'
    )

    class Meta:
        unique_together = ('codename', 'org')  # same codename can't exist twice in same org

    def __str__(self):
        return f"{self.org.name} — {self.name}"
    

class Role(models.Model):
    """
    Granular staff position, e.g. 'Accountant', 'Librarian', 'Principal'.
    Student / Teacher / Owner / Guardian / Vendor are fixed top-level roles
    on CustomUser.role and never go through this table — only Staff users do.
    """

    org = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="roles",
        null=True,
        blank=True,
        help_text=_("Leave blank for a system-wide role not tied to one org."),
    )
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["org", "name"], name="unique_role_name_per_org"),
        ]

    def __str__(self):
        return self.name


class UserRole(models.Model):
    """
    Assigns a granular Role to a Staff user. One role per user at a time.
    """

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="user_role",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,  # can't delete a role while users hold it
        related_name="user_roles",
    )

    def clean(self):
        super().clean()
        if self.user_id and self.user.role != CustomUser.RoleChoices.STAFF:
            raise ValidationError(
                _("UserRole can only be assigned to users whose top-level role is Staff.")
            )

    def __str__(self):
        return f"{self.user.email} — {self.role.name}"
    

class RolePermission(TimestampModel):
    """
    Explicit through table for Role → Permission relationship.
    Using a through table instead of a simple ManyToMany gives us
    created_at tracking — we know when a permission was added to a role.
    """
    role       = models.ForeignKey(Role, on_delete=models.CASCADE)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('role', 'permission')  # same permission can't be added twice

    def __str__(self):
        return f"{self.role.name} — {self.permission.codename}"
    
    
class UserPermissionOverride(TimestampModel):
    """
    Grants or revokes a specific permission for a specific user
    regardless of their role.
    
    granted=True  → user gets this permission even if their role doesn't have it
    granted=False → user loses this permission even if their role has it
    """
    user       = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.CASCADE,
        related_name='permission_overrides'
    )
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name='user_overrides'
    )
    granted    = models.BooleanField()  # True = grant, False = revoke

    class Meta:
        unique_together = ('user', 'permission')  # one override per permission per user

    def __str__(self):
        state = "granted" if self.granted else "revoked"
        return f"{self.user.email} — {self.permission.codename} {state}"
