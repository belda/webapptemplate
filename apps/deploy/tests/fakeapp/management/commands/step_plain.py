from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "An ordinary command, which is not a post-deploy step."

    def handle(self, *args, **options):
        self.stdout.write("nothing to see")
