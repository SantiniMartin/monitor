from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        (
            "evaluaciones_educativas",
            "0005_examencontexto_rename_lecturaomr_examenmatematica",
        ),
    ]

    operations = [
        *[
            migrations.AlterField(
                model_name="examencontexto",
                name=f"item_{item}",
                field=models.CharField(blank=True, default="", max_length=1),
            )
            for item in (2, 3, 5, 6, 9, 10, 11, 12, 13, 15, 16, 17)
        ],
    ]
