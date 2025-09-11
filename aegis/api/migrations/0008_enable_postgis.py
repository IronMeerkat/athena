from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0007_rag_schema_and_doc"),
    ]

    operations = [
        migrations.RunSQL(
            sql="CREATE EXTENSION IF NOT EXISTS postgis;",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]


