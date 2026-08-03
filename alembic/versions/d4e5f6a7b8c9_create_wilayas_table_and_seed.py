"""create wilayas table and seed the 58 wilayas

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-03 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# (code, name_fr, name_ar, name_en, latitude, longitude)
# Official Algerian order 01→58. Coordinates are the wilaya chef-lieu centroid,
# sufficient for a default map viewport (ADR-0005).
WILAYAS: list[tuple[str, str, str, str, float, float]] = [
    ("01", "Adrar", "أدرار", "Adrar", 27.874200, -0.294100),
    ("02", "Chlef", "الشلف", "Chlef", 36.169500, 1.334400),
    ("03", "Laghouat", "الأغواط", "Laghouat", 33.800800, 2.865200),
    ("04", "Oum El Bouaghi", "أم البواقي", "Oum El Bouaghi", 35.877700, 7.113500),
    ("05", "Batna", "باتنة", "Batna", 35.555900, 6.174100),
    ("06", "Béjaïa", "بجاية", "Bejaia", 36.751300, 5.056200),
    ("07", "Biskra", "بسكرة", "Biskra", 34.850400, 5.728100),
    ("08", "Béchar", "بشار", "Bechar", 31.617000, -2.216000),
    ("09", "Blida", "البليدة", "Blida", 36.470300, 2.828700),
    ("10", "Bouira", "البويرة", "Bouira", 36.375200, 3.902100),
    ("11", "Tamanrasset", "تمنراست", "Tamanrasset", 22.785000, 5.522800),
    ("12", "Tébessa", "تبسة", "Tebessa", 35.404200, 8.124300),
    ("13", "Tlemcen", "تلمسان", "Tlemcen", 34.878400, -1.315000),
    ("14", "Tiaret", "تيارت", "Tiaret", 35.371000, 1.317000),
    ("15", "Tizi Ouzou", "تيزي وزو", "Tizi Ouzou", 36.717200, 4.048700),
    ("16", "Alger", "الجزائر", "Algiers", 36.753800, 3.058800),
    ("17", "Djelfa", "الجلفة", "Djelfa", 34.672800, 3.263000),
    ("18", "Jijel", "جيجل", "Jijel", 36.821900, 5.766700),
    ("19", "Sétif", "سطيف", "Setif", 36.190600, 5.415500),
    ("20", "Saïda", "سعيدة", "Saida", 34.830300, 0.151700),
    ("21", "Skikda", "سكيكدة", "Skikda", 36.879100, 6.906400),
    ("22", "Sidi Bel Abbès", "سيدي بلعباس", "Sidi Bel Abbes", 35.189900, -0.630900),
    ("23", "Annaba", "عنابة", "Annaba", 36.900000, 7.766300),
    ("24", "Guelma", "قالمة", "Guelma", 36.462300, 7.428100),
    ("25", "Constantine", "قسنطينة", "Constantine", 36.365000, 6.614700),
    ("26", "Médéa", "المدية", "Medea", 36.264200, 2.758300),
    ("27", "Mostaganem", "مستغانم", "Mostaganem", 35.931100, 0.089200),
    ("28", "M'Sila", "المسيلة", "M'Sila", 35.705800, 4.541100),
    ("29", "Mascara", "معسكر", "Mascara", 35.396200, 0.140700),
    ("30", "Ouargla", "ورقلة", "Ouargla", 31.949100, 5.325200),
    ("31", "Oran", "وهران", "Oran", 35.696900, -0.633100),
    ("32", "El Bayadh", "البيض", "El Bayadh", 33.680700, 1.019500),
    ("33", "Illizi", "إليزي", "Illizi", 26.483400, 8.483300),
    ("34", "Bordj Bou Arréridj", "برج بوعريريج", "Bordj Bou Arreridj", 36.073900, 4.762100),
    ("35", "Boumerdès", "بومرداس", "Boumerdes", 36.766400, 3.477400),
    ("36", "El Tarf", "الطارف", "El Tarf", 36.767200, 8.313700),
    ("37", "Tindouf", "تندوف", "Tindouf", 27.674200, -8.147400),
    ("38", "Tissemsilt", "تيسمسيلت", "Tissemsilt", 35.607200, 1.811200),
    ("39", "El Oued", "الوادي", "El Oued", 33.356800, 6.863400),
    ("40", "Khenchela", "خنشلة", "Khenchela", 35.435300, 7.143300),
    ("41", "Souk Ahras", "سوق أهراس", "Souk Ahras", 36.286400, 7.951100),
    ("42", "Tipaza", "تيبازة", "Tipaza", 36.589700, 2.447400),
    ("43", "Mila", "ميلة", "Mila", 36.450500, 6.264700),
    ("44", "Aïn Defla", "عين الدفلى", "Ain Defla", 36.264000, 1.967500),
    ("45", "Naâma", "النعامة", "Naama", 33.267000, -0.313400),
    ("46", "Aïn Témouchent", "عين تموشنت", "Ain Temouchent", 35.298700, -1.140900),
    ("47", "Ghardaïa", "غرداية", "Ghardaia", 32.489500, 3.673400),
    ("48", "Relizane", "غليزان", "Relizane", 35.737300, 0.555800),
    ("49", "Timimoun", "تيميمون", "Timimoun", 29.263400, 0.231000),
    ("50", "Bordj Badji Mokhtar", "برج باجي مختار", "Bordj Badji Mokhtar", 21.325100, 0.954900),
    ("51", "Ouled Djellal", "أولاد جلال", "Ouled Djellal", 34.421900, 5.063600),
    ("52", "Béni Abbès", "بني عباس", "Beni Abbes", 30.132900, -2.166700),
    ("53", "In Salah", "عين صالح", "In Salah", 27.193300, 2.480900),
    ("54", "In Guezzam", "عين قزام", "In Guezzam", 19.567100, 5.766200),
    ("55", "Touggourt", "تقرت", "Touggourt", 33.104800, 6.058600),
    ("56", "Djanet", "جانت", "Djanet", 24.554700, 9.484500),
    ("57", "El M'Ghair", "المغير", "El M'Ghair", 33.954600, 5.921400),
    ("58", "El Meniaa", "المنيعة", "El Meniaa", 30.582700, 2.884400),
]


def upgrade() -> None:
    wilayas = op.create_table(
        "wilayas",
        sa.Column("code", sa.CHAR(length=2), nullable=False),
        sa.Column("name_fr", sa.String(length=100), nullable=False),
        sa.Column("name_ar", sa.String(length=100), nullable=False),
        sa.Column("name_en", sa.String(length=100), nullable=False),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.PrimaryKeyConstraint("code"),
    )

    op.bulk_insert(
        wilayas,
        [
            {
                "code": code,
                "name_fr": name_fr,
                "name_ar": name_ar,
                "name_en": name_en,
                "latitude": latitude,
                "longitude": longitude,
            }
            for code, name_fr, name_ar, name_en, latitude, longitude in WILAYAS
        ],
    )


def downgrade() -> None:
    op.drop_table("wilayas")
