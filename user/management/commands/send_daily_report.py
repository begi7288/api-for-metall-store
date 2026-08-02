from django.core.management.base import BaseCommand
from datetime import datetime
from user.telegram_bot import send_daily_report

class Command(BaseCommand):
    help = "Sends daily summary report to Telegram bot."

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Target date in YYYY-MM-DD format (default: yesterday)'
        )

    def handle(self, *args, **options):
        date_str = options.get('date')
        target_date = None

        if date_str:
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                self.stdout.write(self.style.ERROR("Invalid date format! Use YYYY-MM-DD."))
                return

        self.stdout.write("Sending daily report to Telegram...")
        send_daily_report(target_date)
        self.stdout.write(self.style.SUCCESS("Daily report sent successfully!"))
