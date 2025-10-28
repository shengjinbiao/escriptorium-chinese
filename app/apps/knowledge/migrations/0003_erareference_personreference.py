from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("knowledge", "0002_rename_knowledge_l_title_78a3f8_idx_knowledge_l_title_3f6f86_idx_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="EraReference",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("era_id", models.CharField(max_length=128, unique=True)),
                ("era_name", models.CharField(max_length=128)),
                ("dynasty", models.CharField(max_length=128)),
                ("emperor", models.CharField(blank=True, max_length=128)),
                ("start_year_ce", models.IntegerField()),
                ("end_year_ce", models.IntegerField()),
                ("start_year_cn", models.CharField(blank=True, max_length=128)),
                ("end_year_cn", models.CharField(blank=True, max_length=128)),
                ("applicable_regions", models.CharField(blank=True, max_length=255)),
                ("source_refs", models.JSONField(blank=True, default=list)),
                ("notes", models.TextField(blank=True)),
            ],
            options={
                "verbose_name": "Era Reference",
                "verbose_name_plural": "Era References",
                "ordering": ["start_year_ce", "era_id"],
            },
        ),
        migrations.CreateModel(
            name="PersonReference",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("person_id", models.CharField(max_length=128, unique=True)),
                ("name", models.CharField(max_length=128)),
                ("courtesy_name", models.CharField(blank=True, max_length=128)),
                ("aliases", models.JSONField(blank=True, default=list)),
                ("gender", models.CharField(blank=True, max_length=32)),
                ("dynasty", models.CharField(max_length=128)),
                ("birth_year", models.IntegerField(blank=True, null=True)),
                ("death_year", models.IntegerField(blank=True, null=True)),
                ("positions", models.JSONField(blank=True, default=list)),
                ("works", models.JSONField(blank=True, default=list)),
                ("related_events", models.JSONField(blank=True, default=list)),
                ("biography_summary", models.TextField(blank=True)),
                ("source_refs", models.JSONField(blank=True, default=list)),
                ("notes", models.TextField(blank=True)),
                (
                    "origin_place",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="notable_people",
                        to="knowledge.placereference",
                    ),
                ),
            ],
            options={
                "verbose_name": "Person Reference",
                "verbose_name_plural": "Person References",
                "ordering": ["name"],
            },
        ),
        migrations.AddIndex(
            model_name="erareference",
            index=models.Index(fields=["era_name"], name="knowledge_e_era_nam_06782d_idx"),
        ),
        migrations.AddIndex(
            model_name="erareference",
            index=models.Index(fields=["dynasty"], name="knowledge_e_dynasty_5a6c85_idx"),
        ),
        migrations.AddIndex(
            model_name="personreference",
            index=models.Index(fields=["name"], name="knowledge_p_name_6e91df_idx"),
        ),
        migrations.AddIndex(
            model_name="personreference",
            index=models.Index(fields=["dynasty"], name="knowledge_p_dynasty_625909_idx"),
        ),
    ]
