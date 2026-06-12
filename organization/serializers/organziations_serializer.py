from rest_framework import serializers
from organization.models import Organization
from core.models import AddressDetail, ContactDetail
class OrganizationPublicSerializer(serializers.ModelSerializer):
    logo = serializers.SerializerMethodField()
    cover_picture = serializers.SerializerMethodField()
    class Meta:
        model = Organization
        fields = (
            "id",
            "name",
            "logo",
            "address",
            "motto",
            "primary_color",
            "secondary_color",
            "cover_picture",
        )
        read_only_fields = fields

    def get_logo(self, obj):
        request = self.context.get("request")
        if obj.logo and request:
            return request.build_absolute_uri(obj.logo.url)
        return None

    def get_cover_picture(self, obj):
        request = self.context.get("request")
        if obj.cover_picture and request:
            return request.build_absolute_uri(obj.cover_picture.url)
        return None
    
from organization.models import SubOrganization


class SubOrganizationSerializer(serializers.ModelSerializer):
    """
    Handles SubOrganization CRUD with embedded contact/address details
    (write_only inputs, flattened into the response via to_representation).
    """
    phone_number  = serializers.CharField(max_length=20, required=False, allow_blank=True, write_only=True)
    phone_number2 = serializers.CharField(max_length=20, required=False, allow_blank=True, write_only=True)
    email         = serializers.EmailField(required=False, allow_blank=True, write_only=True)
    country  = serializers.CharField(max_length=100, required=False, allow_blank=True, write_only=True)
    province = serializers.CharField(max_length=100, required=False, allow_blank=True, write_only=True)
    district = serializers.CharField(max_length=100, required=False, allow_blank=True, write_only=True)
    city     = serializers.CharField(max_length=100, required=False, allow_blank=True, write_only=True)

    class Meta:
        model  = SubOrganization
        fields = [
            'uuid', 'name', 'description', 'created_at', 'updated_at',
            'phone_number', 'phone_number2', 'email',
            'country', 'province', 'district', 'city',
        ]
        read_only_fields = ['uuid', 'created_at', 'updated_at']

    def validate_name(self, value):
        org = self.context['org']
        qs = SubOrganization.objects.filter(org=org, name=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A sub-organization with this name already exists.")
        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for f in ['phone_number', 'phone_number2', 'email', 'country', 'province', 'district', 'city']:
            data.pop(f, None)

        if instance.contact:
            data['phone_number']  = instance.contact.phone_number
            data['phone_number2'] = instance.contact.phone_number2
            data['email']         = instance.contact.email
        else:
            data['phone_number'] = data['phone_number2'] = data['email'] = None

        if instance.address_detail:
            data['country']  = instance.address_detail.country
            data['province'] = instance.address_detail.province
            data['district'] = instance.address_detail.district
            data['city']     = instance.address_detail.city
        else:
            data['country'] = data['province'] = data['district'] = data['city'] = None

        return data

    def create(self, validated_data):
        contact_fields = {k: validated_data.pop(k) for k in ['phone_number', 'phone_number2', 'email'] if k in validated_data}
        address_fields = {k: validated_data.pop(k) for k in ['country', 'province', 'district', 'city'] if k in validated_data}
        org = self.context['org']

        suborg = SubOrganization.objects.create(org=org, **validated_data)

        if contact_fields.get('phone_number'):
            suborg.contact = ContactDetail.objects.create(
                **{'phone_number': '', 'phone_number2': '', 'email': '', **contact_fields}
            )
        if address_fields.get('country'):
            suborg.address_detail = AddressDetail.objects.create(
                **{'country': '', 'province': '', 'district': '', 'city': '', **address_fields}
            )
        if contact_fields.get('phone_number') or address_fields.get('country'):
            suborg.save()

        return suborg

    def update(self, instance, validated_data):
        contact_fields = {k: validated_data.pop(k) for k in ['phone_number', 'phone_number2', 'email'] if k in validated_data}
        address_fields = {k: validated_data.pop(k) for k in ['country', 'province', 'district', 'city'] if k in validated_data}

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if contact_fields:
            if instance.contact:
                for f, v in contact_fields.items():
                    setattr(instance.contact, f, v)
                instance.contact.save()
            else:
                instance.contact = ContactDetail.objects.create(
                    **{'phone_number': '', 'phone_number2': '', 'email': '', **contact_fields}
                )

        if address_fields:
            if instance.address_detail:
                for f, v in address_fields.items():
                    setattr(instance.address_detail, f, v)
                instance.address_detail.save()
            else:
                instance.address_detail = AddressDetail.objects.create(
                    **{'country': '', 'province': '', 'district': '', 'city': '', **address_fields}
                )

        instance.save()
        return instance