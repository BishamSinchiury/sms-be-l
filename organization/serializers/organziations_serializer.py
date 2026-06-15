from rest_framework import serializers
from organization.models import Organization, SubOrganization
from core.models import AddressDetail, ContactDetail


class OrganizationPublicSerializer(serializers.ModelSerializer):
    # ... unchanged, as provided ...
    logo          = serializers.SerializerMethodField()
    cover_picture = serializers.SerializerMethodField()
    phone_number  = serializers.SerializerMethodField()
    phone_number2 = serializers.SerializerMethodField()
    email         = serializers.SerializerMethodField()
    country   = serializers.SerializerMethodField()
    province  = serializers.SerializerMethodField()
    district  = serializers.SerializerMethodField()
    city      = serializers.SerializerMethodField()
    latitude  = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()

    class Meta:
        model  = Organization
        fields = (
            "id", "name", "logo", "motto", "primary_color", "secondary_color",
            "cover_picture", "phone_number", "phone_number2", "email",
            "country", "province", "district", "city", "latitude", "longitude",
        )
        read_only_fields = fields

    def _contact(self, obj):
        return obj.contact if obj.contact else None

    def _address(self, obj):
        return obj.address_detail if obj.address_detail else None

    def get_logo(self, obj):
        request = self.context.get("request")
        if obj.logo and request:
            return request.build_absolute_uri(obj.logo.url)
        return obj.logo.url if obj.logo else None

    def get_cover_picture(self, obj):
        request = self.context.get("request")
        if obj.cover_picture and request:
            return request.build_absolute_uri(obj.cover_picture.url)
        return obj.cover_picture.url if obj.cover_picture else None

    def get_phone_number(self, obj):
        c = self._contact(obj)
        return c.phone_number if c else None

    def get_phone_number2(self, obj):
        c = self._contact(obj)
        return c.phone_number2 if c else None

    def get_email(self, obj):
        c = self._contact(obj)
        return c.email if c else None

    def get_country(self, obj):
        a = self._address(obj)
        return a.country if a else None

    def get_province(self, obj):
        a = self._address(obj)
        return a.province if a else None

    def get_district(self, obj):
        a = self._address(obj)
        return a.district if a else None

    def get_city(self, obj):
        a = self._address(obj)
        return a.city if a else None

    def get_latitude(self, obj):
        a = self._address(obj)
        if a and a.latitude is not None:
            return round(float(a.latitude), 6)
        return None

    def get_longitude(self, obj):
        a = self._address(obj)
        if a and a.longitude is not None:
            return round(float(a.longitude), 6)
        return None


# ─── Sub Organization: List/Card view ────────────────────────────────────────

class SubOrganizationListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for the card/list view.
    """
    completion_percent = serializers.SerializerMethodField()

    class Meta:
        model  = SubOrganization
        fields = ['uuid', 'name', 'description', 'completion_percent', 'created_at', 'updated_at']
        read_only_fields = fields

    def get_completion_percent(self, obj):
        fields_to_check = []

        if obj.contact:
            fields_to_check += [obj.contact.phone_number, obj.contact.email]
        else:
            fields_to_check += [None, None]

        if obj.address_detail:
            fields_to_check += [
                obj.address_detail.country,
                obj.address_detail.province,
                obj.address_detail.district,
                obj.address_detail.city,
            ]
        else:
            fields_to_check += [None, None, None, None]

        fields_to_check += [obj.name, obj.description]

        filled = sum(1 for f in fields_to_check if f not in (None, ""))
        total = len(fields_to_check)
        return round((filled / total) * 100) if total else 0


# ─── Sub Organization: Basic info (name, description) ────────────────────────

class SubOrgBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model  = SubOrganization
        fields = ['uuid', 'name', 'description', 'created_at', 'updated_at']
        read_only_fields = ['uuid', 'created_at', 'updated_at']

    def validate_name(self, value):
        org = self.context['org']
        qs = SubOrganization.objects.filter(org=org, name=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A sub-organization with this name already exists.")
        return value


# ─── Sub Organization: Contact ────────────────────────────────────────────────

class SubOrgContactSerializer(serializers.Serializer):
    phone_number  = serializers.CharField(max_length=20, required=False, allow_blank=True)
    phone_number2 = serializers.CharField(max_length=20, required=False, allow_blank=True)
    email         = serializers.EmailField(required=False, allow_blank=True)

    def update(self, instance, validated_data):
        """
        `instance` is the SubOrganization instance.
        """
        if instance.contact:
            for f, v in validated_data.items():
                setattr(instance.contact, f, v)
            instance.contact.save()
        else:
            instance.contact = ContactDetail.objects.create(
                **{'phone_number': '', 'phone_number2': '', 'email': '', **validated_data}
            )
            instance.save()
        return instance

    def to_representation(self, instance):
        """
        `instance` here is a SubOrganization (or None).
        Extracts the contact if it exists.
        """
        contact = instance.contact if instance else None
        if contact is None:
            return {'phone_number': None, 'phone_number2': None, 'email': None}
        return {
            'phone_number': contact.phone_number,
            'phone_number2': contact.phone_number2,
            'email': contact.email,
        }


# ─── Sub Organization: Address ────────────────────────────────────────────────

class SubOrgAddressSerializer(serializers.Serializer):
    country   = serializers.CharField(max_length=100, required=False, allow_blank=True)
    province  = serializers.CharField(max_length=100, required=False, allow_blank=True)
    district  = serializers.CharField(max_length=100, required=False, allow_blank=True)
    city      = serializers.CharField(max_length=100, required=False, allow_blank=True)
    latitude  = serializers.FloatField(required=False, allow_null=True)
    longitude = serializers.FloatField(required=False, allow_null=True)

    def update(self, instance, validated_data):
        """
        `instance` is the SubOrganization instance.
        """
        if instance.address_detail:
            for f, v in validated_data.items():
                setattr(instance.address_detail, f, v)
            instance.address_detail.save()
        else:
            instance.address_detail = AddressDetail.objects.create(
                **{'country': '', 'province': '', 'district': '', 'city': '', **validated_data}
            )
            instance.save()
        return instance

    def to_representation(self, instance):
        """
        `instance` here is a SubOrganization (or None).
        Extracts the address_detail if it exists.
        """
        addr = instance.address_detail if instance else None
        if addr is None:
            return {
                'country': None, 'province': None, 'district': None,
                'city': None, 'latitude': None, 'longitude': None,
            }
        return {
            'country': addr.country,
            'province': addr.province,
            'district': addr.district,
            'city': addr.city,
            'latitude': round(float(addr.latitude), 6) if addr.latitude is not None else None,
            'longitude': round(float(addr.longitude), 6) if addr.longitude is not None else None,
        }


# ─── Sub Organization: Full detail (for profile view) ─────────────────────────

class SubOrganizationSerializer(serializers.ModelSerializer):
    """
    Full read/write view of a sub-org, flattening contact/address into the response.
    Used for create (AddSubOrgForm) and read (detail view).
    """
    # These accept input but are also output via to_representation
    phone_number  = serializers.CharField(required=False, allow_blank=True)
    phone_number2 = serializers.CharField(required=False, allow_blank=True)
    email         = serializers.EmailField(required=False, allow_blank=True)
    country   = serializers.CharField(required=False, allow_blank=True)
    province  = serializers.CharField(required=False, allow_blank=True)
    district  = serializers.CharField(required=False, allow_blank=True)
    city      = serializers.CharField(required=False, allow_blank=True)
    latitude  = serializers.FloatField(required=False, allow_null=True)
    longitude = serializers.FloatField(required=False, allow_null=True)

    class Meta:
        model  = SubOrganization
        fields = [
            'uuid', 'name', 'description', 'created_at', 'updated_at',
            'phone_number', 'phone_number2', 'email',
            'country', 'province', 'district', 'city', 'latitude', 'longitude',
        ]
        read_only_fields = ['uuid', 'created_at', 'updated_at']

    def to_representation(self, instance):
        """Flatten contact/address into the response."""
        data = super().to_representation(instance)
        if instance.contact:
            data['phone_number']  = instance.contact.phone_number
            data['phone_number2'] = instance.contact.phone_number2
            data['email']         = instance.contact.email
        else:
            data['phone_number']  = None
            data['phone_number2'] = None
            data['email']         = None
        a = instance.address_detail
        if a:
            data['country']   = a.country
            data['province']  = a.province
            data['district']  = a.district
            data['city']      = a.city
            data['latitude']  = round(float(a.latitude), 6) if a.latitude is not None else None
            data['longitude'] = round(float(a.longitude), 6) if a.longitude is not None else None
        else:
            data['country']   = None
            data['province']  = None
            data['district']  = None
            data['city']      = None
            data['latitude']  = None
            data['longitude'] = None
        return data

    def create(self, validated_data):
        validated_data['org'] = self.context['org']

        # Extract contact/address data before creation — they're not model fields
        contact_data = {
            'phone_number': validated_data.pop('phone_number', ''),
            'phone_number2': validated_data.pop('phone_number2', ''),
            'email': validated_data.pop('email', ''),
        }
        address_data = {
            'country': validated_data.pop('country', ''),
            'province': validated_data.pop('province', ''),
            'district': validated_data.pop('district', ''),
            'city': validated_data.pop('city', ''),
        }

        suborg = super().create(validated_data)

        # Create related records if any data was provided
        if any(contact_data.values()):
            suborg.contact = ContactDetail.objects.create(**contact_data)
        if any(address_data.values()):
            suborg.address_detail = AddressDetail.objects.create(**address_data)
        if any(contact_data.values()) or any(address_data.values()):
            suborg.save(update_fields=['contact', 'address_detail'])

        return suborg
