"""Writes tiny SQLite files shaped like the Kaggle olist.sqlite, for the loader to load."""

import sqlite3
from pathlib import Path
from typing import Any

# The source's 11 tables and their columns, as the Kaggle file has them.
TABLES = {
    "customers": "customer_id customer_unique_id customer_zip_code_prefix customer_city "
    "customer_state",
    "geolocation": "geolocation_zip_code_prefix geolocation_lat geolocation_lng geolocation_city "
    "geolocation_state",
    "order_items": "order_id order_item_id product_id seller_id shipping_limit_date price "
    "freight_value",
    "order_payments": "order_id payment_sequential payment_type payment_installments payment_value",
    "order_reviews": "review_id order_id review_score review_comment_title "
    "review_comment_message review_creation_date review_answer_timestamp",
    "orders": "order_id customer_id order_status order_purchase_timestamp order_approved_at "
    "order_delivered_carrier_date order_delivered_customer_date order_estimated_delivery_date",
    "products": "product_id product_category_name product_name_lenght product_description_lenght "
    "product_photos_qty product_weight_g product_length_cm product_height_cm product_width_cm",
    "sellers": "seller_id seller_zip_code_prefix seller_city seller_state",
    "product_category_name_translation": "product_category_name product_category_name_english",
    "leads_qualified": "mql_id first_contact_date landing_page_id origin",
    "leads_closed": "mql_id seller_id sdr_id sr_id won_date business_segment lead_type "
    "lead_behaviour_profile has_company has_gtin average_stock business_type "
    "declared_product_catalog_size declared_monthly_revenue",
}


def write_olist(path: Path, **rows: list[dict[str, Any]]) -> Path:
    """Every table exists; tables not given are empty. Missing columns are NULL."""
    path.unlink(missing_ok=True)
    with sqlite3.connect(path) as db:
        for table, cols in TABLES.items():
            names = cols.split()
            db.execute(f"create table {table} ({', '.join(names)})")
            db.executemany(
                f"insert into {table} values ({', '.join('?' * len(names))})",
                [[r.get(n) for n in names] for r in rows.get(table, [])],
            )
    db.close()
    return path
