"""
Creates a new ToS entry from an html file.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):

    help = 'Update the Terms of Service with a new HTML file'

    def handle(self, *args, **options):
        if len(args) == 0:
            self.stdout.write("Usage: manage.py update_eula filename.html")
            return

        filename = args[0]

        try:
            fh = open(filename, 'rb')
        except IOError:
            self.stdout.write("File not found")

        #late import saves time during ./manage.py help
        from tos.models import TermsOfService

        content = fh.read()

        tos = TermsOfService.objects.create(active=True,
                                            content=content)

        self.stdout.write("Created new tos as of %s" % tos.created)
