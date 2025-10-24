"""
Serializers for API responses.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from . import models

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Public representation of a user."""

    display_name = serializers.CharField(source="get_full_name", read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "display_name"]
        read_only_fields = ["id", "display_name"]


class RegisterSerializer(serializers.Serializer):
    """Serializer used for user self-registration."""

    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    first_name = serializers.CharField(max_length=150, allow_blank=True, required=False)
    last_name = serializers.CharField(max_length=150, allow_blank=True, required=False)

    default_error_messages = {
        "username_exists": _("A user with that username already exists."),
        "email_exists": _("A user with that email already exists."),
    }

    def validate_username(self, value: str) -> str:
        username = value.strip()
        if not username:
            raise serializers.ValidationError(_("Username cannot be blank."))
        if User.objects.filter(username__iexact=username).exists():
            self.fail("username_exists")
        return username

    def validate_email(self, value: str) -> str:
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            self.fail("email_exists")
        return email

    def validate_password(self, value: str) -> str:
        validate_password(value)
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    """Serializer used for credential authentication."""

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    remember_me = serializers.BooleanField(required=False, default=False)


class GameSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Game
        fields = [
            "id",
            "steam_appid",
            "name",
            "steam_url",
            "website",
            "developers",
            "publishers",
            "categories",
            "genres",
            "tags",
            "latest_release_date",
            "latest_detection_stage",
            "latest_api_response_type",
        ]


class GameSnapshotSerializer(serializers.ModelSerializer):
    game = GameSerializer()

    class Meta:
        model = models.GameSnapshot
        fields = [
            "id",
            "game",
            "batch_id",
            "detection_stage",
            "api_response_type",
            "potential_duplicate",
            "discovery_date",
            "ingested_for_date",
            "release_date_raw",
            "description",
            "supported_languages",
            "followers",
            "wishlists_est",
            "wishlist_rank",
            "source_categories",
            "source_genres",
            "source_tags",
        ]


class SwipeActionSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = models.SwipeAction
        fields = ["id", "user", "game", "batch", "action", "note", "created_at"]
        read_only_fields = ["id", "created_at", "user"]


class WatchlistEntrySerializer(serializers.ModelSerializer):
    game = GameSerializer()

    class Meta:
        model = models.WatchlistEntry
        fields = [
            "id",
            "game",
            "first_detected",
            "last_checked",
            "status_history",
            "current_status",
            "check_count",
            "latest_name",
            "latest_type",
            "metadata",
        ]


class DailySummaryGameSerializer(serializers.Serializer):
    """Aggregated info per game for the daily summary endpoint."""

    game = GameSerializer()
    like_users = UserSerializer(many=True)
    skip_users = UserSerializer(many=True)
    watchlist_users = UserSerializer(many=True)
    total_actions = serializers.IntegerField()


class DailySummarySerializer(serializers.Serializer):
    """Serializer representing the team summary output."""

    date = serializers.DateField()
    total_actions = serializers.IntegerField()
    unique_users = serializers.IntegerField()
    like_count = serializers.IntegerField()
    skip_count = serializers.IntegerField()
    watchlist_count = serializers.IntegerField()
    games = DailySummaryGameSerializer(many=True)


class WishlistMomentumSerializer(serializers.ModelSerializer):
    game = GameSerializer()

    class Meta:
        model = models.WishlistMomentum
        fields = [
            "id",
            "game",
            "window",
            "calc_date",
            "delta_followers",
            "delta_per_day",
            "delta_rate",
            "baseline_value",
            "latest_followers",
            "latest_wishlists_est",
            "percentile",
            "rank",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields
