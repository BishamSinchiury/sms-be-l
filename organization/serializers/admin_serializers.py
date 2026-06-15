import re
from rest_framework import serializers
from organization.models import Organization
from core.models import ContactDetail, AddressDetail, DocumentDetail


# ─── Hex color validator ───────────────────────────────────────────────────────

def validate_hex_color(value):
    """
    Validates that a value is a valid hex color code.
    Accepts: #fff, #ffffff, #FFF, #FFFFFF
    Rejects: fff, #gggggg, #12345, random string
    """
    if not re.match(r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$', value):
        raise serializers.ValidationError(
            f"'{value}' is not a valid hex color. Use format #RRGGBB or #RGB."
        )
    return value


# ─── Section 1: Basic Info ────────────────────────────────────────────────────

class OrgBasicInfoSerializer(serializers.ModelSerializer):
    """
    Handles name, logo, motto, colors, cover.
    Saved independently — other sections not required.
    """
    primary_color   = serializers.CharField(validators=[validate_hex_color])
    secondary_color = serializers.CharField(validators=[validate_hex_color])

    # ImageField stays writable so PATCH with FormData actually saves the file.
    # URL building is handled in to_representation below.
    logo          = serializers.ImageField(required=False, allow_null=True)
    cover_picture = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model  = Organization
        fields = [
            'id',
            'name',
            'logo',
            'motto',
            'primary_color',
            'secondary_color',
            'cover_picture',
            'domain_name',
        ]
        read_only_fields = ['id']

    def to_representation(self, instance):
        """Return absolute URLs for image fields on the way out."""
        data    = super().to_representation(instance)
        request = self.context.get('request')

        if instance.logo:
            data['logo'] = (
                request.build_absolute_uri(instance.logo.url)
                if request else instance.logo.url
            )
        else:
            data['logo'] = None

        if instance.cover_picture:
            data['cover_picture'] = (
                request.build_absolute_uri(instance.cover_picture.url)
                if request else instance.cover_picture.url
            )
        else:
            data['cover_picture'] = None

        return data

    def validate_name(self, value):
        qs = Organization.objects.filter(name=value).exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("An organization with this name already exists.")
        return value


# ─── Section 2: Contact ───────────────────────────────────────────────────────

class OrgContactSerializer(serializers.ModelSerializer):
    """
    Handles phone numbers and contact email.
    Creates ContactDetail if it doesn't exist yet,
    updates it if it does.
    """
    phone_number  = serializers.CharField(max_length=20, write_only=True)
    phone_number2 = serializers.CharField(max_length=20, required=False, allow_blank=True, write_only=True)
    email         = serializers.EmailField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model  = Organization
        fields = ['id', 'phone_number', 'phone_number2', 'email']
        read_only_fields = ['id']

    def validate_phone_number(self, value):
        """
        Basic phone validation — must contain only digits, +, -, spaces, brackets.
        Doesn't enforce a specific format since phone formats vary by country.
        """
        if not re.match(r'^[\d\s\+\-\(\)]+$', value):
            raise serializers.ValidationError(
                "Phone number can only contain digits, spaces, +, -, (, )"
            )
        return value

    def to_representation(self, instance):
        """
        Custom output — include contact fields in response
        even though they're on a related model.
        """
        data = super().to_representation(instance)
        if instance.contact:
            data['phone_number']  = instance.contact.phone_number
            data['phone_number2'] = instance.contact.phone_number2
            data['email']         = instance.contact.email
        else:
            data['phone_number']  = None
            data['phone_number2'] = None
            data['email']         = None
        return data

    def update(self, instance, validated_data):
        """
        Creates ContactDetail if org doesn't have one yet.
        Updates it if it already exists.
        """
        contact_data = {
            'phone_number':  validated_data.get('phone_number'),
            'phone_number2': validated_data.get('phone_number2', ''),
            'email':         validated_data.get('email', ''),
        }

        if instance.contact:
            # Update existing
            for field, value in contact_data.items():
                setattr(instance.contact, field, value)
            instance.contact.save()
        else:
            # Create new and link to org
            contact = ContactDetail.objects.create(**contact_data)
            instance.contact = contact
            instance.save()

        return instance


# ─── Section 3: Address ───────────────────────────────────────────────────────

class OrgAddressSerializer(serializers.ModelSerializer):
    country  = serializers.CharField(max_length=100, write_only=True)
    province = serializers.CharField(max_length=100, write_only=True)
    district = serializers.CharField(max_length=100, write_only=True)
    city     = serializers.CharField(max_length=100, write_only=True)
    latitude  = serializers.DecimalField(
        max_digits=12,
        decimal_places=9,
        required=False,
        allow_null=True,
        write_only=True
    )
    longitude = serializers.DecimalField(
        max_digits=12,
        decimal_places=9,
        required=False,
        allow_null=True,
        write_only=True
    )

    class Meta:
        model  = Organization
        fields = ['id', 'country', 'province', 'district', 'city', 'latitude', 'longitude']
        read_only_fields = ['id']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.address_detail:
            data['country']   = instance.address_detail.country
            data['province']  = instance.address_detail.province
            data['district']  = instance.address_detail.district
            data['city']      = instance.address_detail.city
            data['latitude']  = instance.address_detail.latitude
            data['longitude'] = instance.address_detail.longitude
        else:
            data['country']   = None
            data['province']  = None
            data['district']  = None
            data['city']      = None
            data['latitude']  = None
            data['longitude'] = None
        return data

    def update(self, instance, validated_data):
        address_data = {
            'country':   validated_data.get('country'),
            'province':  validated_data.get('province'),
            'district':  validated_data.get('district'),
            'city':      validated_data.get('city'),
            'latitude':  validated_data.get('latitude'),
            'longitude': validated_data.get('longitude'),
        }

        if instance.address_detail:
            for field, value in address_data.items():
                setattr(instance.address_detail, field, value)
            instance.address_detail.save()
        else:
            address = AddressDetail.objects.create(**address_data)
            instance.address_detail = address
            instance.save()

        return instance


# ─── Section 4: Documents ─────────────────────────────────────────────────────


class OrgDocumentSerializer(serializers.ModelSerializer):
    id_registration = serializers.FileField(
        required=False,
        allow_null=True
    )

    tax_registration = serializers.FileField(
        required=False,
        allow_null=True
    )

    birth_certificate_registration = serializers.FileField(
        required=False,
        allow_null=True
    )

    class Meta:
        model = Organization
        fields = [
            'id',
            'id_registration',
            'tax_registration',
            'birth_certificate_registration',
        ]
        read_only_fields = ['id']

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if instance.document:
            request = self.context.get("request")

            data["id_registration"] = (
                request.build_absolute_uri(instance.document.id_registration.url)
                if instance.document.id_registration and request
                else instance.document.id_registration.url
                if instance.document.id_registration
                else None
            )

            data["tax_registration"] = (
                request.build_absolute_uri(instance.document.tax_registration.url)
                if instance.document.tax_registration and request
                else instance.document.tax_registration.url
                if instance.document.tax_registration
                else None
            )

            data["birth_certificate_registration"] = (
                request.build_absolute_uri(instance.document.birth_certificate_registration.url)
                if instance.document.birth_certificate_registration and request
                else instance.document.birth_certificate_registration.url
                if instance.document.birth_certificate_registration
                else None
            )

        return data

    def update(self, instance, validated_data):
        document_data = {
            field: validated_data.get(field)
            for field in [
                "id_registration",
                "tax_registration",
                "birth_certificate_registration",
            ]
            if field in validated_data
        }

        if instance.document:
            for field, value in document_data.items():
                setattr(instance.document, field, value)

            instance.document.save()
        else:
            document = DocumentDetail.objects.create(**document_data)
            instance.document = document
            instance.save(update_fields=["document"])

        return instance


# ─── Profile Completion Check ─────────────────────────────────────────────────

class OrgProfileCompletionSerializer(serializers.ModelSerializer):
    """
    Returns which sections are complete and which are not.
    Frontend reads this on login to decide whether to show the modal.
    """
    completion = serializers.SerializerMethodField()

    class Meta:
        model  = Organization
        fields = ['id', 'name', 'completion']

    def get_completion(self, instance):
        sections = {
            'basic_info': self._check_basic_info(instance),
            'contact':    self._check_contact(instance),
            'address':    self._check_address(instance),
            'documents':  self._check_documents(instance),
        }
        sections['is_complete'] = all(sections.values())
        return sections

    def _check_basic_info(self, instance):
        return all([
            instance.name,
            instance.logo,
            instance.motto,
            instance.primary_color,
            instance.secondary_color,
            instance.cover_picture,
        ])

    def _check_contact(self, instance):
        if not instance.contact:
            return False
        return bool(instance.contact.phone_number)

    def _check_address(self, instance):
        if not instance.address_detail:
            return False
        return all([
            instance.address_detail.country,
            instance.address_detail.province,
            instance.address_detail.district,
            instance.address_detail.city,
        ])

    def _check_documents(self, instance):
        if not instance.document:
            return False
        return all([
            instance.document.id_registration,
            instance.document.tax_registration,
            instance.document.birth_certificate_registration,
        ])