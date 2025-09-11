from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0011_storekv_ttl_minutes_storevector'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE "graph"."store_vectors" DROP COLUMN IF EXISTS "embedding";
                ALTER TABLE "graph"."store_vectors" ADD COLUMN "embedding" vector(1536) NULL;
            """,
            reverse_sql="""
                ALTER TABLE "graph"."store_vectors" DROP COLUMN IF EXISTS "embedding";
                ALTER TABLE "graph"."store_vectors" ADD COLUMN "embedding" bytea NULL;
            """,
        ),
    ]
