"""Various Peewee models."""
import config

import peewee as pw


db = pw.PostgresqlDatabase(
    config.DB_NAME, user=config.DB_USER, password=config.DB_PASSWORD
)


class BaseModel(pw.Model):
    """A base model, that sets the DB."""

    class Meta:
        """Set the DB and use new table names."""

        database = db
        use_legacy_table_names = False


db.create_tables([])
