from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0008_enable_postgis"),
    ]

    operations = [
        migrations.RunSQL(
            sql="CREATE SCHEMA IF NOT EXISTS graph;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.CreateModel(
            name="StoreKV",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("prefix", models.TextField()),
                ("key", models.TextField()),
                ("value", models.JSONField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": 'graph"."store',
                "indexes": [
                    models.Index(fields=["prefix"], name="store_prefix_idx"),
                ],
                "unique_together": {("prefix", "key")},
            },
        ),
    ]


