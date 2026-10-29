-- The 11 source tables, columns as in the Kaggle olist.sqlite. Timestamps are naive
-- São Paulo local time and are never converted. Columns whose source type is uncertain
-- (zip prefixes, has_company, average_stock…) stay text.

CREATE TABLE IF NOT EXISTS raw.customers (
    customer_id text,
    customer_unique_id text,
    customer_zip_code_prefix text,
    customer_city text,
    customer_state text
);

CREATE TABLE IF NOT EXISTS raw.geolocation (
    geolocation_zip_code_prefix text,
    geolocation_lat double precision,
    geolocation_lng double precision,
    geolocation_city text,
    geolocation_state text
);

CREATE TABLE IF NOT EXISTS raw.order_items (
    order_id text,
    order_item_id integer,
    product_id text,
    seller_id text,
    shipping_limit_date timestamp,
    price numeric,
    freight_value numeric
);

CREATE TABLE IF NOT EXISTS raw.order_payments (
    order_id text,
    payment_sequential integer,
    payment_type text,
    payment_installments integer,
    payment_value numeric
);

CREATE TABLE IF NOT EXISTS raw.order_reviews (
    review_id text,
    order_id text,
    review_score integer,
    review_comment_title text,
    review_comment_message text,
    review_creation_date timestamp,
    review_answer_timestamp timestamp
);

CREATE TABLE IF NOT EXISTS raw.orders (
    order_id text,
    customer_id text,
    order_status text,
    order_purchase_timestamp timestamp,
    order_approved_at timestamp,
    order_delivered_carrier_date timestamp,
    order_delivered_customer_date timestamp,
    order_estimated_delivery_date timestamp
);

CREATE TABLE IF NOT EXISTS raw.products (
    product_id text,
    product_category_name text,
    product_name_lenght numeric,
    product_description_lenght numeric,
    product_photos_qty numeric,
    product_weight_g numeric,
    product_length_cm numeric,
    product_height_cm numeric,
    product_width_cm numeric
);

CREATE TABLE IF NOT EXISTS raw.sellers (
    seller_id text,
    seller_zip_code_prefix text,
    seller_city text,
    seller_state text
);

CREATE TABLE IF NOT EXISTS raw.product_category_name_translation (
    product_category_name text,
    product_category_name_english text
);

CREATE TABLE IF NOT EXISTS raw.leads_qualified (
    mql_id text,
    first_contact_date timestamp,
    landing_page_id text,
    origin text
);

CREATE TABLE IF NOT EXISTS raw.leads_closed (
    mql_id text,
    seller_id text,
    sdr_id text,
    sr_id text,
    won_date timestamp,
    business_segment text,
    lead_type text,
    lead_behaviour_profile text,
    has_company text,
    has_gtin text,
    average_stock text,
    business_type text,
    declared_product_catalog_size numeric,
    declared_monthly_revenue numeric
);
