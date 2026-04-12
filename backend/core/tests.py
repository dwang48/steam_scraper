from __future__ import annotations

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from core import models
from core.management.commands import rescan_and_purge_nsfw_games
from core.nsfw import classify_nsfw_from_row


class NSFWRulesTests(SimpleTestCase):
    def test_adult_content_counts_as_nsfw(self) -> None:
        is_nsfw, reasons = classify_nsfw_from_row(
            {
                "name": "Test Game",
                "description": "This release contains adult content.",
                "tags": "",
            }
        )

        self.assertTrue(is_nsfw)
        self.assertEqual(reasons, ["description:adult content"])


class RescanAndPurgeNSFWGamesCommandTests(TestCase):
    def setUp(self) -> None:
        super().setUp()
        now = timezone.now()
        self.batch = models.DiscoveryBatch.objects.create(
            source_name="test_source",
            run_started_at=now,
            run_completed_at=now,
            ingested_for_date=now.date(),
        )

        self.local_nsfw_game = models.Game.objects.create(
            steam_appid=101,
            name="Moonlight Archive",
        )
        models.GameSnapshot.objects.create(
            game=self.local_nsfw_game,
            batch=self.batch,
            ingested_for_date=now.date(),
            description="Contains adult content and explicit scenes.",
            source_tags="visual novel",
        )

        self.safe_game = models.Game.objects.create(
            steam_appid=202,
            name="Cozy Farm",
        )
        models.GameSnapshot.objects.create(
            game=self.safe_game,
            batch=self.batch,
            ingested_for_date=now.date(),
            description="A peaceful farming adventure.",
            source_tags="farming;relaxing",
        )

    @patch("core.management.commands.rescan_and_purge_nsfw_games._scan_one")
    def test_command_uses_local_cleanup_only_by_default(self, mock_scan_one) -> None:
        stdout = StringIO()

        call_command("rescan_and_purge_nsfw_games", "--dry-run", stdout=stdout)

        mock_scan_one.assert_not_called()
        output = stdout.getvalue()
        self.assertIn("local_hits=1", output)
        self.assertIn("live_queue=0", output)
        self.assertIn("[dry-run] NSFW → 101 | Moonlight Archive | description:adult content", output)

    @patch("core.management.commands.rescan_and_purge_nsfw_games._scan_one")
    def test_live_fetch_skips_games_already_flagged_locally(self, mock_scan_one) -> None:
        mock_scan_one.return_value = rescan_and_purge_nsfw_games.LiveScanResult(
            game_id=self.safe_game.id,
            steam_appid=self.safe_game.steam_appid,
            details={},
            errors=[],
        )
        stdout = StringIO()

        call_command(
            "rescan_and_purge_nsfw_games",
            "--dry-run",
            "--live-fetch",
            "--max-workers=1",
            stdout=stdout,
        )

        self.assertEqual(mock_scan_one.call_count, 1)
        self.assertEqual(mock_scan_one.call_args[0][1], self.safe_game.steam_appid)
        self.assertIn("live_queue=1", stdout.getvalue())
