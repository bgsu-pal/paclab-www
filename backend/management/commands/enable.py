from django.core.management.base import BaseCommand
from django.core.management import call_command
from website.models import Filter, Transform

'''Enable Command

Usage: manage.py enable BACKEND_NAME
Installs and enables all items in the database associated with the specified backend.
'''
class Command(BaseCommand):
    help = 'Installs all filters from the specified backend into the database'

    def add_arguments(self, parser):
        parser.add_argument('backend')

    def handle(self, *args, **options):
        backend = options['backend']
        try:
            call_command('loaddata', backend + '_filters')
            for myfilter in Filter.objects.filter(associated_backend__name=backend):
                myfilter.enabled = True
                myfilter.save()
        except:
            pass
        try:
            call_command('loaddata', backend + '_transforms')
            for mytransform in Transform.objects.filter(associated_backend__name=backend):
                mytransform.enabled = True
                mytransform.save()
        except:
            pass
