DROP TABLE IF EXISTS table1;
CREATE TABLE IF NOT EXISTS table1 (
    id INT AUTO_INCREMENT PRIMARY KEY,           -- INTEGER
    active BIT,                                  -- BIT
    age INT,                                     -- INTEGER
    is_active BOOLEAN,                           -- BOOLEAN
    price DOUBLE,                                -- DOUBLE
    created_at DATE,                             -- DATE
    updated_at DATETIME,                         -- DATETIME
    last_login TIMESTAMP,                        -- TIMESTAMP
    duration TIME,                               -- TIME
    year YEAR,                                    -- YEAR
    name CHAR(50),                               -- CHAR
    description TEXT,                            -- TEXT
    data BLOB                                    -- BLOB
);

DROP TABLE IF EXISTS table2;
CREATE TABLE IF NOT EXISTS table2 (
    id INT AUTO_INCREMENT PRIMARY KEY,           -- INTEGER
    status BIT,                                  -- BIT
    count INT,                                   -- INTEGER
    active BOOLEAN,                              -- BOOLEAN
    cost DOUBLE,                                 -- DOUBLE
    start_date DATE,                             -- DATE
    timestamp DATETIME,                          -- DATETIME
    event_time TIMESTAMP,                        -- TIMESTAMP
    duration TIME,                               -- TIME
    year YEAR,                                    -- YEAR
    label CHAR(50),                              -- CHAR
    note TEXT,                                   -- TEXT
    image_data BLOB                              -- BLOB
);

-- 插入数据
INSERT INTO table1 (active, age, is_active, price, created_at, updated_at, last_login, duration, year, name, description, data)
VALUES (1, 25, TRUE, 99.99, '2023-12-01', '2023-12-01 10:00:00', '2023-12-01 12:30:00', '01:30:00', 2023, 'John Doe', 'Sample description', X'FFD8FFE000104A4649460001010100600060000000FFDB0043');
INSERT INTO table1 (active, age, is_active, price, created_at, updated_at, last_login, duration, year, name, description, data)
VALUES (0, 30, FALSE, 150.75, '2023-11-20', '2023-11-20 14:00:00', '2023-11-20 16:00:00', '02:00:00', 2022, 'Alice Smith', 'Another description', X'FFD8FFE000104A4649460001010100600060000000FFDB0043');
INSERT INTO table1 (active, age, is_active, price, created_at, updated_at, last_login, duration, year, name, description, data)
VALUES (1, 22, TRUE, 80.50, '2023-10-10', '2023-10-10 09:00:00', '2023-10-10 11:30:00', '01:00:00', 2024, 'Bob Johnson', 'Description here', X'FFD8FFE000104A4649460001010100600060000000FFDB0043');
INSERT INTO table1 (active, age, is_active, price, created_at, updated_at, last_login, duration, year, name, description, data)
VALUES (0, 28, FALSE, 120.60, '2023-09-01', '2023-09-01 08:30:00', '2023-09-01 10:00:00', '01:15:00', 2025, 'Eva White', 'Test description', X'FFD8FFE000104A4649460001010100600060000000FFDB0043');
INSERT INTO table1 (active, age, is_active, price, created_at, updated_at, last_login, duration, year, name, description, data)
VALUES (1, 35, TRUE, 200.25, '2023-08-15', '2023-08-15 11:00:00', '2023-08-15 13:00:00', '01:45:00', 2023, 'Charlie Brown', 'Sample text for description', X'FFD8FFE000104A4649460001010100600060000000FFDB0043');

-- 插入数据
INSERT INTO table2 (status, count, active, cost, start_date, timestamp, event_time, duration, year, label, note, image_data)
VALUES (1, 100, TRUE, 500.50, '2023-12-01', '2023-12-01 10:00:00', '2023-12-01 12:30:00', '01:00:00', 2023, 'Group A', 'First event', X'FFD8FFE000104A4649460001010100600060000000FFDB0043');
INSERT INTO table2 (status, count, active, cost, start_date, timestamp, event_time, duration, year, label, note, image_data)
VALUES (0, 150, FALSE, 450.30, '2023-11-20', '2023-11-20 14:00:00', '2023-11-20 16:00:00', '02:00:00', 2022, 'Group B', 'Second event', X'FFD8FFE000104A4649460001010100600060000000FFDB0043');
INSERT INTO table2 (status, count, active, cost, start_date, timestamp, event_time, duration, year, label, note, image_data)
VALUES (1, 80, TRUE, 320.25, '2023-10-10', '2023-10-10 09:00:00', '2023-10-10 11:30:00', '01:15:00', 2024, 'Group C', 'Third event', X'FFD8FFE000104A4649460001010100600060000000FFDB0043');
INSERT INTO table2 (status, count, active, cost, start_date, timestamp, event_time, duration, year, label, note, image_data)
VALUES (0, 200, FALSE, 700.75, '2023-09-01', '2023-09-01 08:30:00', '2023-09-01 10:00:00', '02:00:00', 2025, 'Group D', 'Fourth event', X'FFD8FFE000104A4649460001010100600060000000FFDB0043');
INSERT INTO table2 (status, count, active, cost, start_date, timestamp, event_time, duration, year, label, note, image_data)
VALUES (1, 120, TRUE, 600.60, '2023-08-15', '2023-08-15 11:00:00', '2023-08-15 13:00:00', '01:30:00', 2023, 'Group E', 'Fifth event', X'FFD8FFE000104A4649460001010100600060000000FFDB0043');
