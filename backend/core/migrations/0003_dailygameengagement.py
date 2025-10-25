from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_wishlistmomentum"),
    ]

    operations = [
        migrations.CreateModel(
            name="DailyGameEngagement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("summary_date", models.DateField(help_text="Business date (UTC) the engagement was recorded for.")),
                ("likes", models.PositiveIntegerField(default=0)),
                ("skips", models.PositiveIntegerField(default=0)),
                ("watchlists", models.PositiveIntegerField(default=0)),
                ("unique_likers", models.PositiveIntegerField(default=0)),
                ("unique_skeptics", models.PositiveIntegerField(default=0)),
                ("total_actions", models.PositiveIntegerField(default=0)),
                ("computed_at", models.DateTimeField(auto_now_add=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                (
                    "game",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="daily_engagements",
                        to="core.game",
                    ),
                ),
            ],
            options={
                "ordering": ["-summary_date", "-likes", "game__name"],
                "unique_together": {("game", "summary_date")},
            },
        ),
        migrations.AddIndex(
            model_name="dailygameengagement",
            index=models.Index(fields=["summary_date", "-likes"], name="core_daily_summary_84f7ba_idx"),
        ),
        migrations.AddIndex(
            model_name="dailygameengagement",
            index=models.Index(fields=["summary_date", "-total_actions"], name="core_daily_summary_416ca5_idx"),
        ),
    ]
