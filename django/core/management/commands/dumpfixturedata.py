from django.core.management.commands.dumpdata import Command as DumpCommand
from django.core.management import call_command
from StringIO import StringIO
from django.conf import settings
from random import randint
from django.db.migrations.loader import MigrationLoader
from django.db import connection
from django.db.migrations.writer import MIGRATION_TEMPLATE
from django import get_version
from django.utils.timezone import now
import os


class Command(DumpCommand):

    migration_template = """# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
import django.core.management.commands.loaddata
from django.db import DEFAULT_DB_ALIAS
import os

fixture_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'fixtures'))
fixture_filename = '{{ json_file }}'


def load_fixture(apps, schema_editor):
    fixture_file = os.path.join(fixture_dir, fixture_filename)
    load_command = django.core.management.commands.loaddata.Command()

    options = {
        "ignore": False,
        "database": DEFAULT_DB_ALIAS,
        "app_label": None,
        "verbosity": 0,
        "exclude": [],
        "project_apps": apps
    }

    load_command.handle(fixture_file, **options)
    print(1/0)


class Migration(migrations.Migration):
    dependencies = [
        {% autoescape off %}{{ dependencies }}{% endautoescape %}
    ]

    operations = [
        migrations.RunPython(load_fixture),
    ]


"""
    def handle(self, *app_labels, **options):

        out = StringIO()
        options['stdout'] = out
        call_command("dumpdata", *app_labels, **options)
        out.seek(0)
        output = out.read()

        json_file = "data"+str(randint(999, 9999))+".json"
        main_app = app_labels[0].split(".")[0]
        migrations_path = os.path.join(settings.BASE_DIR, main_app, "migrations")
        fixture_path = os.path.join(migrations_path, "fixtures")
        json_path = os.path.join(fixture_path, json_file)

        if not os.path.isdir(fixture_path):
            os.mkdir(fixture_path)

        with open(json_path, "w") as f:
            f.write(output)

        migration_loader = MigrationLoader(connection)
        unique_apps = set([app.split('.')[0] for app in app_labels])
        latest_migrations_from_all_apps = [str(list(migration_loader.graph.leaf_nodes(app))[0])+"," for app in unique_apps]

        call_command('makemigrations', main_app, '--empty')


        new_migration_loader = MigrationLoader(connection)
        latest_migration_from_main_app = list(new_migration_loader.graph.leaf_nodes(main_app))[0]

        latest_migration_file_path = os.path.join(migrations_path, latest_migration_from_main_app[1] + ".py" )

        dependencies = "\n        ".join(latest_migrations_from_all_apps)

        sorted_imports = []
        sorted_imports.append("from django.db import migrations")
        sorted_imports.append("import django.core.management.commands.loaddata")
        sorted_imports.append("from django.db import DEFAULT_DB_ALIAS")
        sorted_imports.append("import os")
        sorted_imports.append("\n")
        sorted_imports.append("fixture_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'fixtures'))")
        sorted_imports.append("fixture_filename = '"+json_file+"'")
        sorted_imports.append("\n")
        sorted_imports.append("def load_fixture(apps, schema_editor):")
        sorted_imports.append("    fixture_file = os.path.join(fixture_dir, fixture_filename)")
        sorted_imports.append("    load_command = django.core.management.commands.loaddata.Command()")
        sorted_imports.append("")
        sorted_imports.append("    options = {")
        sorted_imports.append("        'ignore': False,")
        sorted_imports.append("        'database': DEFAULT_DB_ALIAS,")
        sorted_imports.append("        'app_label': None,")
        sorted_imports.append("        'verbosity': 0,")
        sorted_imports.append("        'exclude': [],")
        sorted_imports.append("        'project_apps': apps")
        sorted_imports.append("    }")
        sorted_imports.append("")
        sorted_imports.append("    load_command.handle(fixture_file, **options)")
        sorted_imports.append("    print(1 / 0)")

        items = {
            "replaces_str": "",
            "initial_str": "",
            "operations": "         migrations.RunPython(load_fixture),\n",
            "dependencies": "        "+dependencies+"\n",
            "version": get_version(),
            "timestamp": now().strftime("%Y-%m-%d %H:%M"),
            "imports": "\n".join(sorted_imports) + "\n"
        }

        migration_text = (MIGRATION_TEMPLATE % items).encode("utf8")

        with open(latest_migration_file_path, "wb") as fh:
            fh.write(migration_text)



