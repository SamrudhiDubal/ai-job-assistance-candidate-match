"""Create a portal administrator. Admins cannot sign up through the website."""
import getpass

from django.core.management.base import BaseCommand, CommandError

from accounts.models import User


class Command(BaseCommand):
    help = "Create an administrator account"

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--name", default="Administrator")
        parser.add_argument("--password", help="Leave out to be asked for it")

    def handle(self, *args, email, name, password, **opts):
        if User.objects.filter(email=email.lower()).exists():
            raise CommandError("A user with that email already exists.")
        password = password or getpass.getpass("Password: ")
        User.objects.create_superuser(email=email, password=password, name=name)
        self.stdout.write(self.style.SUCCESS(f"Administrator {email} created."))
