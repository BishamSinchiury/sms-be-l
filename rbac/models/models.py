import uuid
from django.db import models
from organization.models import Organization
from core.models import TimestampModel



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
    
class Role(TimestampModel):
    """
    A named collection of permissions scoped to an organization.
    Examples: Student, Teacher, Staff, Vendor, Owner
    
    Sysadmin creates roles and assigns permissions to them.
    Users are then assigned a role.
    """
    uuid        = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name        = models.CharField(max_length=50)
    description = models.CharField(max_length=255, blank=True)
    org         = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='roles'
    )
    permissions = models.ManyToManyField(
        Permission,
        through='RolePermission',
        related_name='roles',
        blank=True
    )

    class Meta:
        unique_together = ('name', 'org')  # "Teacher" can exist in org1 and org2

    def __str__(self):
        return f"{self.org.name} — {self.name}"
    

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
    
class UserRole(TimestampModel):
    """
    Assigns a role to a user within an org.
    A user can only have one role at a time per org.
    """
    user = models.OneToOneField(
        'users.CustomUser',
        on_delete=models.CASCADE,
        related_name='user_role'
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,  # can't delete a role if users are assigned to it
        related_name='user_roles'
    )

    def __str__(self):
        return f"{self.user.email} — {self.role.name}"
    
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
