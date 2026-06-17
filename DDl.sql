CREATE database iluma_orders_dev;

CREATE schema core;

CREATE schema orders;

CREATE schema auth;

CREATE schema configuration;

CREATE SCHEMA operation;

CREATE SCHEMA supplier;

create schema sync;

CREATE TABLE core.customer (
    customer_id INT generated always AS identity primary key,
    customer_name VARCHAR(500) NOT NULL,
    customer_code VARCHAR(50) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    default_language VARCHAR(50) NOT NULL DEFAULT 'en',
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE core.product (
    product_id INT generated always AS identity primary key,
    product_name VARCHAR(500) NOT NULL,
    code VARCHAR(50) NOT NULL,
    description text
);

CREATE TABLE core.business (
    business_id INT generated always AS identity primary key,
    business_name VARCHAR(250) NOT NULL,
    code VARCHAR(250) NOT NULL
);

CREATE TABLE configuration.process (
    process_id INT generated always AS identity primary key,
    process_name VARCHAR(250) NOT NULL,
    business_id INT references core.business (business_id),
    description text,
    created_at TIMESTAMP NOT NULL
);

create table configuration.process_fields (
    process_field_id int generated always as identity primary key,
    process_id int not null references configuration.process (process_id),
    field_name varchar(250) not null,
    -- field_type varchar(250) not null, maybe in the future
    created_at timestamp not null
);

CREATE TABLE configuration.step (
    step_id INT generated always AS identity primary key,
    step_name VARCHAR(255) NOT NULL,
    process_id INT NOT NULL references configuration.process (process_id),
    step_order INT NOT NULL,
    details text,
    created_at TIMESTAMP NOT NULL,
    visible_to_customer BOOLEAN NOT NULL
);

CREATE TABLE configuration.step_state (
    step_state_id INT generated always AS identity primary key,
    step_state_name VARCHAR(250) NOT NULL
);

CREATE TABLE orders.order_state (
    order_state_id INT generated always AS identity primary key,
    order_state_name VARCHAR(250) NOT NULL
);

CREATE TABLE orders.order (
    order_id int4 generated always AS identity NOT NULL,
    order_code VARCHAR(250) NOT NULL,
    customer_id int4 NOT NULL,
    process_id int4 NULL,
    order_state_id int4 NOT NULL,
    created_at TIMESTAMP NOT NULL,
    description text NULL,
    business_id int not null,
    constraint order_pkey primary key (order_id),
    constraint order_customer_id_fkey foreign key (customer_id) references core.customer (customer_id),
    constraint order_order_state_id_fkey foreign key (order_state_id) references orders.order_state (order_state_id),
    constraint order_process_id_fkey foreign key (process_id) references configuration.process (process_id),
    foreign key (business_id) references core.business (business_id)
);

create table orders.order_fields (
    order_field_id int generated always as identity primary key,
    order_id int not null references orders.order (order_id),
    process_field_id int not null references configuration.process_fields (process_field_id),
    field_value text,
    updated_at timestamp not null
);

CREATE TABLE orders.order_product (
    order_product_id INT generated always AS identity primary key,
    order_id INT NOT NULL references orders.order (order_id),
    product_id INT NOT NULL references core.product (product_id),
    quantity numeric NOT NULL -- Measurement unit?
);

CREATE TABLE orders.order_step (
    order_step_id INT generated always AS identity primary key,
    order_id INT NOT NULL references orders.order (order_id),
    step_id INT NOT NULL references configuration.step (step_id),
    updated_at TIMESTAMP NOT NULL,
    complete BOOLEAN NOT NULL,
    step_state_id INT NOT NULL references configuration.step_state (step_state_id),
    notes text
);

CREATE TABLE auth.user (
    user_id INT generated always AS identity primary key,
    user_name VARCHAR(500) NOT NULL,
    email VARCHAR(250) NOT NULL,
    sub_id_usu VARCHAR(250) NOT NULL,
    customer_id INT references core.customer (customer_id) --user_type????dd
);

CREATE TABLE orders.message (
    message_id INT generated always AS identity primary key,
    order_id INT NOT NULL references orders.order (order_id),
    sender_id INT NULL references auth.user (user_id),
    message_content text,
    created_at TIMESTAMP NOT NULL,
    sender varchar(500) not null,
    title text null
);

CREATE TABLE orders.document (
    document_id INT generated always AS identity primary key,
    document_name VARCHAR(500) NOT NULL,
    document_key VARCHAR(500) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    CURRENT_VERSION INT DEFAULT 1,
    order_id INT NOT NULL references orders.order (order_id),
    order_step_id INT NULL references orders.order_step (order_step_id) -- document_type ??
);

CREATE TABLE orders.document_history (
    document_history_id INT generated always AS identity primary key,
    created_at TIMESTAMP NOT NULL,
    version_number INT NOT NULL,
    document_key VARCHAR(500) NOT NULL,
    change_reason text,
    changed_by INT references auth.user (user_id),
    document_id INT references orders.document (document_id),
    change_timestamp TIMESTAMP NOT NULL
);

create table core.customer_preferences (
    customer_preferences_id int generated always as identity not null,
    customer_id int not null,
    allow_order_messages_notification bool not null default true,
    allow_new_file_uploaded_notification bool not null default true,
    allow_new_file_version_uploaded_notification bool not null default true,
    allow_order_status_update_notification bool not null default true,
    foreign key (customer_id) references core.customer (customer_id)
)
--------- VIEWS
-- orders.vw_orders source
CREATE
OR REPLACE VIEW orders.vw_orders AS
SELECT
    o.order_id,
    o.order_code,
    o.customer_id,
    o.process_id,
    o.order_state_id,
    o.created_at,
    C.customer_name,
    C.email,
    C.customer_code,
    p.process_name,
    os.order_state_name,
    o.description,
    o.business_id
FROM
    orders."order" o
    JOIN core.customer C ON C.customer_id = o.customer_id
    LEFT JOIN configuration.process p ON p.process_id = o.process_id
    JOIN orders.order_state os ON os.order_state_id = o.order_state_id;

CREATE
OR REPLACE VIEW orders.vw_order_step AS
SELECT
    os.*,
    s.step_name,
    s.details,
    s.step_order,
    s.visible_to_customer,
    ss.step_state_name
FROM
    orders.order_step os
    JOIN "configuration".step s ON s.step_id = os.step_id
    JOIN "configuration".step_state ss ON ss.step_state_id = os.step_state_id
ORDER BY
    s.step_order ASC;

CREATE VIEW orders.vw_document AS
SELECT
    d.*,
    s.step_name,
    s.step_order,
    s.visible_to_customer
FROM
    orders."document" d
    LEFT JOIN orders.order_step os ON os.order_step_id = d.order_step_id
    LEFT JOIN "configuration".step s ON s.step_id = os.step_id;

create view orders.vw_document_history as
select
    dh.*,
    d.document_name
from
    orders.document_history dh
    join orders."document" d on d.document_id = dh.document_id
order by
    dh.version_number desc;

create
or replace view orders.vw_message as
select
    m.message_id,
    m.order_id,
    m.sender_id,
    m.message_content,
    m.created_at,
    m.title,
    o.order_code,
    coalesce(u.user_name, m.sender) as sender,
    o.customer_id
from
    orders.message m
    join orders."order" o on o.order_id = m.order_id
    left join auth."user" u on u.user_id = m.sender_id
where
    m.message_id in (
        select
            max(me.message_id) as message_id
        from
            orders.message me
        group by
            me.order_id
        having
            max(me.created_at) = max(me.created_at)
    );

create view orders.vw_order_fields as
select
    o.*,
    pf.field_name
from
    orders.order_fields as o
    join "configuration".process_fields pf on o.process_field_id = pf.process_field_id;

create view orders.vw_order_product as
select
    op.*,
    p.product_name,
    p.code
from
    orders.order_product op
    join core.product p on op.product_id = p.product_id;



CREATE TABLE sync.sales_order (
    creation_date DATE,
    sales_organization VARCHAR(10),
    sales_document_type VARCHAR(10),
    sales_order_number VARCHAR(20) NOT NULL, -- Part of composite PK
    customer VARCHAR(20),
    division_code VARCHAR(10),
    division_number VARCHAR(10),
    currency VARCHAR(3),
    invoicing_company VARCHAR(10),
    created_by VARCHAR(50),
    uen VARCHAR(10),
    center VARCHAR(10),
    item_number VARCHAR(10) NOT NULL, -- Part of composite PK
    material_code VARCHAR(20),
    requested_quantity NUMERIC(18, 3),
    unit_of_measure VARCHAR(5),
    confirmed_quantity NUMERIC(18, 3),
    unit_price NUMERIC(18, 2),
    currency2 VARCHAR(3), -- Note: Potentially redundant with currency
    net_value NUMERIC(18, 2),
    internal_costs NUMERIC(18, 2),
    profit_center VARCHAR(20),
    order_reason VARCHAR(50) NULL, -- Explicitly allow NULL
    sales_order_number2 VARCHAR(20), -- Note: Potentially redundant
    delivery_status CHAR(1),
    sales_order_number3 VARCHAR(20), -- Note: Potentially redundant
    delivery_date DATE,
    customer_name VARCHAR(255),
    ctc_code VARCHAR(20),
    ctc_name VARCHAR(255),
    recipient_code VARCHAR(20),
    recipient VARCHAR(255),
    material VARCHAR(255), -- Material description
    blocking_note VARCHAR(255) NULL, -- Explicitly allow NULL
    credit_check_status VARCHAR(10) NULL, -- Explicitly allow NULL
    credit_control_area VARCHAR(10),
    customer_credit_limit NUMERIC(18, 2),
    total_committed NUMERIC(18, 2),
    available_credit_limit NUMERIC(18, 2),
    article_group VARCHAR(10),
    article_group_description VARCHAR(255),
    material_group VARCHAR(10),
    material_group_description VARCHAR(255),
    material_group_two VARCHAR(10),
    material_group_two_description VARCHAR(255),
    -- Define the composite primary key
    PRIMARY KEY (sales_order_number, item_number)
);

CREATE OR REPLACE VIEW sync.vw_sales_order_without_details
AS SELECT sales_order.creation_date,
    sales_order.sales_organization,
    sales_order.sales_order_number,
    sales_order.customer,
    sales_order.division_code,
    sales_order.currency,
    sales_order.invoicing_company,
    sales_order.center,
    sales_order.customer_name,
    sales_order.recipient_code,
    sales_order.recipient,
    count(*) AS materials
   FROM sync.sales_order
   where sales_order.division_code is not null and sales_order.center is not null
  GROUP BY sales_order.creation_date, sales_order.sales_organization, sales_order.sales_order_number, sales_order.customer, sales_order.division_code, sales_order.currency, sales_order.invoicing_company, sales_order.center, sales_order.customer_name, sales_order.recipient_code, sales_order.recipient
  ORDER BY sales_order.creation_date desc

CREATE TABLE auth.user_business (
    user_business_id INT generated always AS identity primary key,
    user_id INT NOT NULL REFERENCES auth.user (user_id),
    business_id INT NOT NULL REFERENCES core.business (business_id),
    created_at TIMESTAMP NOT NULL,
    UNIQUE(user_id, business_id)
);

CREATE TABLE core.incoterm (
    incoterm_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    incoterm_code VARCHAR(30) NOT NULL,
    incoterm_name VARCHAR(250) NOT NULL
);

CREATE TABLE core.currency (
    currency_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    currency_name VARCHAR(250) NOT NULL
);

CREATE TABLE core.unit_type (
    unit_type_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    unit_type_name VARCHAR(250) NOT NULL,
    unit_weight FLOAT
);

CREATE TABLE core.location (
    location_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    location VARCHAR(250) NOT NULL,
    address VARCHAR(250),
    client_id INTEGER,
    FOREIGN KEY (client_id) REFERENCES core.customer(customer_id)
);

CREATE TABLE core.measurement_unit (
    measurement_unit_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    measurement_unit_name VARCHAR(250) NOT NULL
);

CREATE TABLE core.service_type (
    service_type_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    service_type_name VARCHAR(50) NOT NULL
);

CREATE TABLE core.hazard_type (
    hazard_type_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    hazard_type_name VARCHAR(250) NOT NULL
);

CREATE TABLE core.vehicle_type (
    vehicle_type_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    vehicle_type_name VARCHAR(250) NOT NULL
);



CREATE TABLE operation.operation_status(
    operation_status_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    operation_status_name VARCHAR(200) NOT NULL
);


CREATE TABLE operation.operation_type (
    operation_type_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    operation_type_name VARCHAR(250) NOT NULL
);

CREATE TABLE operation.operation (
    operation_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    operation_code varchar UNIQUE ,
    operation_type_id INT NOT NULL,
    location_origin_id INT NOT NULL,
    service_type_id INT NOT NULL,
    user_id INT NOT NULL,
    requires_escort BOOLEAN  NULL,
    load_date TIMESTAMP NOT NULL,
    validity_date TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL,
    observation VARCHAR(2000),
    operation_status_id INTEGER,
    FOREIGN KEY (operation_status_id) REFERENCES operation.operation_status(operation_status_id),
    FOREIGN KEY (location_origin_id) REFERENCES core.location(location_id),
    FOREIGN KEY (operation_type_id) REFERENCES operation.operation_type(operation_type_id),
    FOREIGN KEY (service_type_id) REFERENCES core.service_type(service_type_id),
    FOREIGN KEY (user_id) REFERENCES auth."user"(user_id)
);


CREATE TABLE operation.operation_detail (
    operation_detail_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    unit_type_id INT NOT NULL,
    operation_id INT NOT NULL,
    location_id INT NOT NULL,
    unit_count INT NOT NULL,
    unit_weight float NOT NULL,
    net_weight FLOAT,
    gross_weight FLOAT,
    height FLOAT,
    width FLOAT,
    length FLOAT,
    FOREIGN KEY (unit_type_id) REFERENCES core.unit_type(unit_type_id),
    FOREIGN KEY (operation_id) REFERENCES operation.operation(operation_id),
    FOREIGN KEY (location_id) REFERENCES core.location(location_id)
);

CREATE TABLE operation.operation_hazard_type (
    operation_hazard_type_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    operation_id INT NOT NULL,
    hazard_type_id INT NOT NULL,
    FOREIGN KEY (operation_id) REFERENCES operation.operation(operation_id),
    FOREIGN KEY (hazard_type_id) REFERENCES core.hazard_type(hazard_type_id)
);

CREATE TABLE operation.operation_vehicle_type (
    operation_vehicle_type_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    operation_id INT NOT NULL,
    vehicle_type_id INT NOT NULL,
    FOREIGN KEY (operation_id) REFERENCES operation.operation(operation_id),
    FOREIGN KEY (vehicle_type_id) REFERENCES core.vehicle_type(vehicle_type_id)
);

CREATE TABLE operation.operation_incoterm (
    operation_incoterm_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    operation_id INT NOT NULL,
    incoterm_id INT NOT NULL,
    FOREIGN KEY (operation_id) REFERENCES operation.operation(operation_id),
    FOREIGN KEY (incoterm_id) REFERENCES core.incoterm(incoterm_id)
);



CREATE TABLE supplier.supplier (
    supplier_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    supplier_name VARCHAR(250) NOT NULL,
	status BOOLEAN DEFAULT TRUE
);

CREATE TABLE supplier.email (
    email_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email VARCHAR(250) NOT NULL,
    supplier_id INT NOT NULL,
    FOREIGN KEY (supplier_id) REFERENCES supplier.supplier(supplier_id)
);

CREATE TABLE supplier.supplier_operation (
    supplier_operation_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    supplier_id INT NOT NULL,
    operation_id INT NOT NULL,
    key UUID NOT NULL,
    FOREIGN KEY (supplier_id) REFERENCES supplier.supplier(supplier_id),
    FOREIGN KEY (operation_id) REFERENCES operation.operation(operation_id)
);



CREATE TABLE core.offer (
    offer_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    offer_code VARCHAR(250),
    incoterm_id INT ,
    operation_id INT NOT NULL,
    supplier_id INT NOT NULL,
    currency_id INT NOT NULL,
    valid_until TIMESTAMP,
    transit_time INT,
    transshipment BOOLEAN,
    free_days INT,
    tariff FLOAT,
    free_loading boolean,
    free_charge BOOLEAN,
    is_availability_date BOOLEAN,
    load_date TIMESTAMP,
    observation VARCHAR(2000),
    transporter VARCHAR(250),
    min FLOAT,
    amount FLOAT,
    wm FLOAT,
    imo FLOAT,
    container_size_20 FLOAT,
    container_size_40 FLOAT,
    freight_percentage FLOAT,
    document_bl FLOAT,
    preparation_fee_bl FLOAT,
    mounting_dismounting FLOAT,
    food_grade FLOAT,
    positioning FLOAT,
    thc_origin FLOAT,
    special_handling FLOAT,
    vgm FLOAT,
    custom_ams FLOAT,
    consolidation_lcl FLOAT,
    destination_bl FLOAT,
    destination_cont FLOAT,
    free_days_destination INT,
    total_tariff FLOAT,
    selected BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (incoterm_id) REFERENCES core.incoterm(incoterm_id),
    FOREIGN KEY (operation_id) REFERENCES operation.operation(operation_id),
    FOREIGN KEY (supplier_id) REFERENCES supplier.supplier(supplier_id),
    FOREIGN KEY (currency_id) REFERENCES core.currency(currency_id)
);



CREATE TABLE core.offer_location (
    offer_location_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    offer_id INT NOT NULL,
    location_id INT NOT NULL,
    tariff FLOAT NOT NULL,
    FOREIGN KEY (offer_id) REFERENCES core.offer(offer_id)
);

CREATE TABLE supplier.supplier_operation_email (
    supplier_operation_email_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    supplier_operation_id INT NOT NULL,
    email_id INT NOT NULL
);


ALTER TABLE supplier.email ADD COLUMN is_primary BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE supplier.email ADD COLUMN status BOOLEAN NOT NULL DEFAULT TRUE;


ALTER TABLE orders.order_product ADD unit_of_measure varchar(50) NOT NULL;

-- Changes May 1st 2025

-- Add business_id to customer table
ALTER TABLE core.customer ADD COLUMN business_id INT;
UPDATE core.customer SET business_id = 1; -- Set a default value for existing records
ALTER TABLE core.customer ALTER COLUMN business_id SET NOT NULL;
ALTER TABLE core.customer ADD CONSTRAINT customer_business_id_fkey FOREIGN KEY (business_id) REFERENCES core.business (business_id);

-- Add business_id to product table
ALTER TABLE core.product ADD COLUMN business_id INT;
UPDATE core.product SET business_id = 1; -- Set a default value for existing records
ALTER TABLE core.product ALTER COLUMN business_id SET NOT NULL;
ALTER TABLE core.product ADD CONSTRAINT product_business_id_fkey FOREIGN KEY (business_id) REFERENCES core.business (business_id);

-- Create user_business table for many-to-many relationship


-- Add indexes for better performance
CREATE INDEX idx_customer_business_id ON core.customer(business_id);
CREATE INDEX idx_product_business_id ON core.product(business_id);
CREATE INDEX idx_user_business_user_id ON auth.user_business(user_id);
CREATE INDEX idx_user_business_business_id ON auth.user_business(business_id);

-- Add user_type to user table
ALTER TABLE auth.user ADD COLUMN user_type VARCHAR(50) DEFAULT 'customer';

-- Add unit_of_measure column to product table
ALTER TABLE core.product ADD COLUMN unit_of_measure VARCHAR(50) NOT NULL DEFAULT 'pcs';
-- Views
CREATE VIEW core.vw_offer_international AS
SELECT
	o.operation_id,
    o.offer_id,
    s.supplier_name,
    s.supplier_id,
    l."location",
    l.address,
    o.offer_code,
    o.valid_until,
    o.load_date,
    o.tariff,
    c.currency_name,
    i.incoterm_code,
    o.transit_time,
    o.transshipment,
    o.free_days,
    o.transporter,
    o.min,
    o.amount,
    o.wm,
    o.imo,
    o.container_size_20,
    o.container_size_40,
    o.freight_percentage,
    o.document_bl,
    o.preparation_fee_bl,
    o.mounting_dismounting,
    o.food_grade,
    o.positioning,
    o.thc_origin,
    o.special_handling,
    o.vgm,
    o.custom_ams,
    o.consolidation_lcl,
    o.destination_bl,
    o.destination_cont,
    o.selected,
    o.free_days_destination
FROM core.offer o
JOIN supplier.supplier s ON o.supplier_id = s.supplier_id
JOIN core.incoterm i ON o.incoterm_id = i.incoterm_id
JOIN core.currency c ON o.currency_id = c.currency_id
JOIN core.offer_location ol ON o.offer_id = ol.offer_id
JOIN core."location" l ON ol.location_id = l.location_id
WHERE o.incoterm_id IS NOT NULL
ORDER BY s.supplier_name, o.offer_id;



CREATE VIEW core.vw_offer_national AS
SELECT
   	o.operation_id,
    o.offer_id,
    s.supplier_name,
    s.supplier_id,
    c.currency_name,
    o.offer_code,
    o.valid_until,
    o.free_loading ,
    o.load_date,
    o.selected,
    COALESCE(SUM(ol.tariff), 0) AS total_location_tariff,
    COALESCE(
        JSONB_AGG(
            JSONB_BUILD_OBJECT(
                'location', l."location",
                'address', l.address,
                'tariff', ol.tariff
            )
        ) FILTER (WHERE l."location" IS NOT NULL),
        '[]'::jsonb
    ) AS locations_detail
FROM core.offer o
JOIN supplier.supplier s ON o.supplier_id = s.supplier_id
LEFT JOIN core.offer_location ol ON o.offer_id = ol.offer_id
LEFT JOIN core.location l ON ol.location_id = l.location_id
JOIN core.currency c ON o.currency_id = c.currency_id
WHERE o.incoterm_id IS NULL
GROUP BY o.offer_id, s.supplier_name, o.offer_code,c.currency_name, o.valid_until, o.load_date,o.selected,s.supplier_id
ORDER BY s.supplier_name, o.offer_id;



CREATE VIEW supplier.vw_supplier_operation_email AS
SELECT
    so.operation_id,
    s.supplier_id,
    s.supplier_name,
    so."key",
    e.email_id,
    e.is_primary,
    e.email
FROM
    supplier.supplier s
JOIN
    supplier.supplier_operation so ON s.supplier_id = so.supplier_id
JOIN
    supplier.email e ON s.supplier_id = e.supplier_id
JOIN
    supplier.supplier_operation_email soe ON soe.email_id = e.email_id
GROUP BY
    so.operation_id, s.supplier_id, s.supplier_name, e.email,e.email_id,so."key",e.is_primary
ORDER BY
    so.operation_id, s.supplier_id, e.email;


CREATE VIEW operation.vw_operation_detail AS
SELECT
    od.operation_detail_id,
    ut.unit_type_name,
    od.operation_id,
    l.location_id,
    l.location AS destination,
    l.address,
    od.unit_count,
    od.unit_weight,
    od.net_weight,
    od.gross_weight,
    od.height,
    od.width,
    od.length
FROM operation.operation_detail od
LEFT JOIN core.unit_type ut ON od.unit_type_id = ut.unit_type_id
LEFT JOIN core.location l ON od.location_id = l.location_id;
DROP VIEW operation.vw_operation_detail;

CREATE OR REPLACE VIEW core.vw_destinations AS
SELECT DISTINCT
    od.operation_id,
    l.location_id,
    l.location,
    l.address
FROM core.location l
JOIN operation.operation_detail od ON od.location_id = l.location_id;

CREATE OR REPLACE VIEW operation.vw_operation AS
SELECT
    o.operation_id,
    o.operation_code,
    o.user_id,
    u.email,
    ot.operation_type_name,
    loc.location AS location_origin_name,
    st.service_type_name,
    o.requires_escort,
    o.load_date,
    o.created_at,
    o.validity_date,
    o.observation,
    opt.operation_status_name,
    COUNT(DISTINCT off.offer_id) AS offer_count, -- Contar ofertas por operación
    COALESCE(array_agg(DISTINCT inc.incoterm_code) FILTER (WHERE inc.incoterm_id IS NOT NULL), '{}') AS incoterms,
    COALESCE(array_agg(DISTINCT jsonb_build_object(
        'unit_type', ut.unit_type_name,
        'location', loc_det.location,
        'unit_count', od.unit_count,
        'unit_weight', od.unit_weight,
        'net_weight', od.net_weight,
        'gross_weight', od.gross_weight
    )) FILTER (WHERE od.operation_detail_id IS NOT NULL), '{}') AS operation_details
FROM operation.operation o
JOIN operation.operation_type ot ON o.operation_type_id = ot.operation_type_id
JOIN core.location loc ON o.location_origin_id = loc.location_id
JOIN core.service_type st ON o.service_type_id = st.service_type_id
JOIN auth."user" u ON o.user_id = u.user_id
JOIN operation.operation_status opt ON opt.operation_status_id = o.operation_status_id
LEFT JOIN operation.operation_incoterm oi ON o.operation_id = oi.operation_id
LEFT JOIN core.incoterm inc ON oi.incoterm_id = inc.incoterm_id
LEFT JOIN operation.operation_detail od ON o.operation_id = od.operation_id
LEFT JOIN core.unit_type ut ON od.unit_type_id = ut.unit_type_id
LEFT JOIN core.location loc_det ON od.location_id = loc_det.location_id
LEFT JOIN core.offer off ON o.operation_id = off.operation_id
GROUP BY o.operation_id, ot.operation_type_name, loc.location, st.service_type_name, u.user_name, opt.operation_status_name,u.email
ORDER BY o.created_at DESC;



CREATE OR REPLACE VIEW operation.vw_operation_details as
SELECT
    o.operation_id,
    o.operation_code,
    ot.operation_type_name,
    lo.location AS location_origin_name,
    st.service_type_name,
    os.operation_status_name AS operation_status_name,
    o.requires_escort,
    o.load_date,
    o.validity_date,
    o.user_id,
    o.created_at,
    o.observation,
    COUNT(DISTINCT off.offer_id) AS offer_count,
    COALESCE(array_agg(DISTINCT inc.incoterm_code) FILTER (WHERE inc.incoterm_id IS NOT NULL), '{}') AS incoterms,
    COALESCE(array_agg(DISTINCT ht.hazard_type_name) FILTER (WHERE ht.hazard_type_id IS NOT NULL), '{}') AS hazard_types,
    COALESCE(array_agg(DISTINCT vt.vehicle_type_name) FILTER (WHERE vt.vehicle_type_id IS NOT NULL), '{}') AS vehicle_types,
    CASE
        WHEN COUNT(DISTINCT oi.incoterm_id) = 0 THEN true
        ELSE false
    END AS is_local
FROM operation.operation o
LEFT JOIN operation.operation_incoterm oi ON o.operation_id = oi.operation_id
LEFT JOIN core.incoterm inc ON oi.incoterm_id = inc.incoterm_id
LEFT JOIN operation.operation_hazard_type oht ON o.operation_id = oht.operation_id
LEFT JOIN core.hazard_type ht ON oht.hazard_type_id = ht.hazard_type_id
LEFT JOIN operation.operation_vehicle_type ovt ON o.operation_id = ovt.operation_id
LEFT JOIN core.vehicle_type vt  ON ovt.vehicle_type_id = vt.vehicle_type_id
LEFT JOIN operation.operation_type ot ON o.operation_type_id = ot.operation_type_id
LEFT JOIN core.service_type st ON o.service_type_id = st.service_type_id
LEFT JOIN core.location lo ON o.location_origin_id = lo.location_id
LEFT JOIN operation.operation_status os ON o.operation_status_id = os.operation_status_id
LEFT JOIN core.offer off ON o.operation_id = off.operation_id
GROUP BY o.operation_id, ot.operation_type_name,lo.location, st.service_type_name, os.operation_status_name,o.validity_date,o.user_id
ORDER BY o.created_at DESC;

CREATE VIEW supplier.vw_supplier_operation_email AS
SELECT
    so.operation_id,
    s.supplier_id,
    s.supplier_name,
    so."key",
    e.email_id,
    e.is_primary,
    e.email
FROM
    supplier.supplier s
JOIN
    supplier.supplier_operation so ON s.supplier_id = so.supplier_id
JOIN
    supplier.email e ON s.supplier_id = e.supplier_id
JOIN
    supplier.supplier_operation_email soe ON soe.email_id = e.email_id
GROUP BY
    so.operation_id, s.supplier_id, s.supplier_name, e.email,e.email_id,so."key",e.is_primary
ORDER BY
    so.operation_id, s.supplier_id, e.email;
