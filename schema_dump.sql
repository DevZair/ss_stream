-- ss_stream domain schema (Django system tables are created via migrations)
-- Target DB: MySQL 8+ / InnoDB / utf8mb4

SET NAMES utf8mb4;
SET time_zone = "+00:00";

-- Справочники
CREATE TABLE inventory_category (
    id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(150)    NOT NULL UNIQUE,
    description   TEXT            NOT NULL DEFAULT '',
    is_active     BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE inventory_warehouse (
    id         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    code       VARCHAR(20)     NOT NULL UNIQUE,
    name       VARCHAR(150)    NOT NULL UNIQUE,
    location   VARCHAR(255)    NOT NULL,
    created_at DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE inventory_warehouseprofile (
    id                     BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    warehouse_id           BIGINT UNSIGNED NOT NULL UNIQUE,
    manager_name           VARCHAR(255)    NOT NULL DEFAULT '',
    contact_phone          VARCHAR(50)     NOT NULL DEFAULT '',
    capacity               INT UNSIGNED    NOT NULL DEFAULT 0,
    temperature_controlled BOOLEAN         NOT NULL DEFAULT FALSE,
    CONSTRAINT fk_wprofile_warehouse FOREIGN KEY (warehouse_id)
        REFERENCES inventory_warehouse(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE inventory_accesssection (
    id   BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    slug VARCHAR(50)     NOT NULL UNIQUE,
    name VARCHAR(100)    NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Пользователи/сотрудники (опирается на auth_user из Django)
CREATE TABLE inventory_employee (
    id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    user_id     BIGINT UNSIGNED NULL,
    full_name   VARCHAR(255)    NOT NULL,
    position    VARCHAR(50)     NOT NULL,
    status      VARCHAR(20)     NOT NULL,
    warehouse_id BIGINT UNSIGNED NOT NULL,
    CONSTRAINT fk_employee_user FOREIGN KEY (user_id)
        REFERENCES auth_user(id) ON DELETE SET NULL,
    CONSTRAINT fk_employee_warehouse FOREIGN KEY (warehouse_id)
        REFERENCES inventory_warehouse(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE inventory_employee_access_sections (
    id             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    employee_id    BIGINT UNSIGNED NOT NULL,
    accesssection_id BIGINT UNSIGNED NOT NULL,
    CONSTRAINT uq_employee_access UNIQUE (employee_id, accesssection_id),
    CONSTRAINT fk_employee_access_employee FOREIGN KEY (employee_id)
        REFERENCES inventory_employee(id) ON DELETE CASCADE,
    CONSTRAINT fk_employee_access_section FOREIGN KEY (accesssection_id)
        REFERENCES inventory_accesssection(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Товары и остатки
CREATE TABLE inventory_product (
    id             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name           VARCHAR(255)    NOT NULL,
    category_id    BIGINT UNSIGNED NOT NULL,
    purchase_price DECIMAL(12,2)   NOT NULL,
    selling_price  DECIMAL(12,2)   NOT NULL,
    photo          VARCHAR(100)    NULL,
    CONSTRAINT uq_product_name_category UNIQUE (name, category_id),
    CONSTRAINT fk_product_category FOREIGN KEY (category_id)
        REFERENCES inventory_category(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE inventory_stock (
    id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    warehouse_id BIGINT UNSIGNED NOT NULL,
    product_id   BIGINT UNSIGNED NOT NULL,
    quantity     INT UNSIGNED    NOT NULL DEFAULT 0,
    CONSTRAINT uq_stock_wh_product UNIQUE (warehouse_id, product_id),
    CONSTRAINT fk_stock_warehouse FOREIGN KEY (warehouse_id)
        REFERENCES inventory_warehouse(id) ON DELETE CASCADE,
    CONSTRAINT fk_stock_product FOREIGN KEY (product_id)
        REFERENCES inventory_product(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Операции: приход/перемещение/продажи
CREATE TABLE inventory_incoming (
    id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    product_id   BIGINT UNSIGNED NOT NULL,
    warehouse_id BIGINT UNSIGNED NOT NULL,
    quantity     INT UNSIGNED    NOT NULL,
    date         DATE            NOT NULL DEFAULT CURRENT_DATE,
    CONSTRAINT fk_incoming_product FOREIGN KEY (product_id)
        REFERENCES inventory_product(id) ON DELETE RESTRICT,
    CONSTRAINT fk_incoming_warehouse FOREIGN KEY (warehouse_id)
        REFERENCES inventory_warehouse(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE inventory_movement (
    id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    product_id      BIGINT UNSIGNED NOT NULL,
    from_warehouse_id BIGINT UNSIGNED NOT NULL,
    to_warehouse_id BIGINT UNSIGNED NOT NULL,
    quantity        INT UNSIGNED    NOT NULL,
    date            DATE            NOT NULL DEFAULT CURRENT_DATE,
    CONSTRAINT fk_movement_product FOREIGN KEY (product_id)
        REFERENCES inventory_product(id) ON DELETE RESTRICT,
    CONSTRAINT fk_movement_from FOREIGN KEY (from_warehouse_id)
        REFERENCES inventory_warehouse(id) ON DELETE CASCADE,
    CONSTRAINT fk_movement_to FOREIGN KEY (to_warehouse_id)
        REFERENCES inventory_warehouse(id) ON DELETE CASCADE,
    CONSTRAINT chk_movement_diff CHECK (from_warehouse_id <> to_warehouse_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE inventory_sale (
    id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    product_id      BIGINT UNSIGNED NOT NULL,
    warehouse_id    BIGINT UNSIGNED NOT NULL,
    quantity        INT UNSIGNED    NOT NULL,
    price           DECIMAL(12,2)   NOT NULL DEFAULT 0.00,
    total           DECIMAL(12,2)   NOT NULL DEFAULT 0.00,
    payment_method  VARCHAR(10)     NOT NULL,
    cash_amount     DECIMAL(12,2)   NOT NULL DEFAULT 0.00,
    halyk_amount    DECIMAL(12,2)   NOT NULL DEFAULT 0.00,
    kaspi_amount    DECIMAL(12,2)   NOT NULL DEFAULT 0.00,
    payment_details VARCHAR(255)    NOT NULL DEFAULT '',
    seller_id       BIGINT UNSIGNED NULL,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_sale_product FOREIGN KEY (product_id)
        REFERENCES inventory_product(id) ON DELETE RESTRICT,
    CONSTRAINT fk_sale_warehouse FOREIGN KEY (warehouse_id)
        REFERENCES inventory_warehouse(id) ON DELETE CASCADE,
    CONSTRAINT fk_sale_seller FOREIGN KEY (seller_id)
        REFERENCES auth_user(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE inventory_salesreport (
    id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    sale_id      BIGINT UNSIGNED NOT NULL,
    report_type  VARCHAR(20)     NOT NULL DEFAULT 'sale',
    status       VARCHAR(20)     NOT NULL DEFAULT 'final',
    notes        TEXT            NOT NULL DEFAULT '',
    created_at   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_salesreport_sale FOREIGN KEY (sale_id)
        REFERENCES inventory_sale(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Аудит
CREATE TABLE inventory_activitylog (
    id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    user_id      BIGINT UNSIGNED NULL,
    employee_id  BIGINT UNSIGNED NULL,
    action       VARCHAR(255)    NOT NULL,
    entity_type  VARCHAR(50)     NOT NULL DEFAULT '',
    entity_id    BIGINT UNSIGNED NULL,
    details      TEXT            NOT NULL DEFAULT '',
    created_at   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_log_user FOREIGN KEY (user_id)
        REFERENCES auth_user(id) ON DELETE SET NULL,
    CONSTRAINT fk_log_employee FOREIGN KEY (employee_id)
        REFERENCES inventory_employee(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
