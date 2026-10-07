"""Migrations: the amount and its currency are two ordinary, explicit fields."""

import pytest
from django.db import connection, migrations, models
from django.db.migrations.autodetector import MigrationAutodetector
from django.db.migrations.questioner import MigrationQuestioner
from django.db.migrations.state import ModelState, ProjectState

from currency_amount_field import codes
from currency_amount_field.fields import CurrencyCodeField, CurrencyField
from tests.testapp.models import Child, Invoice, OverridingChild

APP = "testapp"


class Questioner(MigrationQuestioner):
    """Answers the one-off-default question the way `makemigrations` would."""

    def ask_not_null_addition(self, field_name, model_name):
        return 0


@pytest.fixture
def drop_scratch_tables():
    yield
    with connection.cursor() as cursor:
        for table in ("testapp_item", "testapp_invoicecopy"):
            cursor.execute(f"DROP TABLE IF EXISTS {table}")


def apply(state, operation):
    """Run one migration operation against the database, like `migrate` does."""
    new_state = state.clone()
    operation.state_forwards(APP, new_state)
    with connection.schema_editor() as editor:
        operation.database_forwards(APP, editor, state, new_state)
    return new_state


def columns(table):
    with connection.cursor() as cursor:
        return [row[1] for row in cursor.execute(f"PRAGMA table_info({table})").fetchall()]


def create_item_table():
    state = apply(
        ProjectState(),
        migrations.CreateModel(
            "Item",
            [
                ("id", models.BigAutoField(primary_key=True)),
                ("name", models.CharField(max_length=20)),
            ],
        ),
    )
    with connection.cursor() as cursor:
        cursor.execute("INSERT INTO testapp_item (name) VALUES ('old row')")
    return state


def changes_between(before, after):
    return MigrationAutodetector(before, after, Questioner())._detect_changes()


def state_of(model_state):
    state = ProjectState()
    state.add_model(model_state)
    return state


# --- adding the fields to a table that already holds rows -----------------------


@pytest.mark.django_db(transaction=True)
def test_adding_a_currency_field_to_a_table_that_has_rows(drop_scratch_tables):
    """Used to fail: NOT NULL constraint failed: new__testapp_item.price_currency"""
    state = create_item_table()
    for operation in [
        migrations.AddField("item", "price", CurrencyField(default_currency="USD", default=0)),
        migrations.AddField("item", "price_currency", CurrencyCodeField(default="USD")),
    ]:
        state = apply(state, operation)

    assert columns("testapp_item") == ["id", "name", "price", "price_currency"]
    with connection.cursor() as cursor:
        rows = cursor.execute("SELECT name, price, price_currency FROM testapp_item").fetchall()
    assert rows == [("old row", 0, "USD")]


@pytest.mark.django_db(transaction=True)
def test_the_amount_alone_adds_only_its_own_column(drop_scratch_tables):
    state = create_item_table()
    state = apply(state, migrations.AddField("item", "price", CurrencyField(default_currency="USD", default=0)))

    assert columns("testapp_item") == ["id", "name", "price"]
    rendered = state.apps.get_model(APP, "Item")
    assert [f.name for f in rendered._meta.local_fields] == ["id", "name", "price"]


@pytest.mark.django_db(transaction=True)
def test_renaming_and_removing_the_two_fields_like_any_others(drop_scratch_tables):
    state = create_item_table()
    for operation in [
        migrations.AddField("item", "price", CurrencyField(default_currency="USD", default=0)),
        migrations.AddField("item", "price_currency", CurrencyCodeField(default="USD")),
        migrations.RenameField("item", "price", "cost"),
        migrations.RenameField("item", "price_currency", "cost_currency"),
        migrations.RemoveField("item", "cost_currency"),
    ]:
        state = apply(state, operation)
    assert columns("testapp_item") == ["id", "name", "cost"]


# --- the rendered state ---------------------------------------------------------


def test_a_migration_state_never_gains_a_hidden_currency_field():
    state = state_of(
        ModelState(APP, "Solo", [("id", models.BigAutoField(primary_key=True)), ("price", CurrencyField())])
    )
    solo = state.apps.get_model(APP, "Solo")
    assert [f.name for f in solo._meta.local_fields] == ["id", "price"]


def test_a_migration_state_keeps_both_fields_exactly_as_listed():
    state = state_of(
        ModelState(
            APP,
            "Pair",
            [
                ("id", models.BigAutoField(primary_key=True)),
                ("price", CurrencyField()),
                ("price_currency", CurrencyCodeField(default="EUR")),
            ],
        )
    )
    pair = state.apps.get_model(APP, "Pair")
    assert [f.name for f in pair._meta.local_fields] == ["id", "price", "price_currency"]
    assert pair._meta.get_field("price_currency").default == "EUR"


# --- what makemigrations writes --------------------------------------------------


def test_a_new_model_is_created_with_both_fields_listed():
    after = state_of(ModelState.from_model(Invoice))
    operation = changes_between(ProjectState(), after)[APP][0].operations[0]

    assert isinstance(operation, migrations.CreateModel)
    assert [name for name, _ in operation.fields] == ["id", "label", "total", "total_currency", "notes"]


@pytest.mark.django_db(transaction=True)
def test_the_migration_made_for_a_new_model_builds_the_whole_table(drop_scratch_tables):
    invoice = ModelState.from_model(Invoice)
    after = state_of(ModelState(APP, "InvoiceCopy", dict(invoice.fields)))

    state = ProjectState()
    for operation in changes_between(ProjectState(), after)[APP][0].operations:
        state = apply(state, operation)

    assert columns("testapp_invoicecopy") == ["id", "label", "total", "total_currency", "notes"]


def test_adding_a_currency_field_to_a_model_produces_two_add_fields():
    fields = {
        name: field
        for name, field in ModelState.from_model(Invoice).fields.items()
        if name not in ("total", "total_currency")
    }
    before = state_of(ModelState(APP, "Invoice", fields))
    after = state_of(ModelState.from_model(Invoice))

    operations = changes_between(before, after)[APP][0].operations
    assert [(type(op).__name__, op.name) for op in operations] == [
        ("AddField", "total"),
        ("AddField", "total_currency"),
    ]


def test_models_that_are_up_to_date_need_no_migration():
    for model in (Invoice, Child, OverridingChild):
        state = state_of(ModelState.from_model(model))
        assert changes_between(state, state.clone()) == {}


def test_the_state_built_from_a_model_matches_the_model_after_a_round_trip():
    """No endless AlterField: the rendered state deconstructs like the model."""
    state = state_of(ModelState.from_model(Invoice))
    rendered = state.apps.get_model(APP, "Invoice")
    again = state_of(ModelState.from_model(rendered))
    assert changes_between(state, again) == {}


def test_an_old_migration_that_spelled_out_every_option_still_matches_the_model():
    """What 1.0.0 wrote: the full currency list on both fields, a blank=True currency."""
    full = list(codes.CURRENCY_CHOICES)
    fields = dict(ModelState.from_model(Invoice).fields)
    fields["total"] = CurrencyField(
        currency_choices=full,
        currency_field_name="total_currency",
        currency_max_length=3,
        decimal_places=2,
        default_currency="USD",
        max_digits=14,
    )
    fields["total_currency"] = CurrencyCodeField(
        blank=True, choices=full, default="USD", max_length=3, verbose_name="currency"
    )
    old = state_of(ModelState(APP, "Invoice", fields))
    new = state_of(ModelState.from_model(Invoice))

    operations = changes_between(old, new)[APP][0].operations
    # The amount field is untouched; the only change is the currency field's
    # blank=True and "currency" label, which has no effect on the database.
    assert [(type(op).__name__, op.name) for op in operations] == [("AlterField", "total_currency")]
