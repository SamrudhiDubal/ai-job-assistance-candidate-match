from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Train the ML and DL resume classifiers and save them to screening/models/"

    def add_arguments(self, parser):
        parser.add_argument("--no-dl", action="store_true", help="Skip the TensorFlow/Keras model")

    def handle(self, *args, no_dl=False, **opts):
        from screening.ml.train import train_all

        metrics = train_all(settings.BASE_DIR, with_dl=not no_dl, log=self.stdout.write)
        self.stdout.write(self.style.SUCCESS(f"Best ML model: {metrics['best_ml_model']}"))
