CREATE TABLE lists (
	id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    name VARCHAR(255) NOT NULL,
    emoji CHAR(4),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE list_items (
	id INT AUTO_INCREMENT PRIMARY KEY,
    list_id INT,
    name VARCHAR(255) NOT NULL,
    url VARCHAR(2083),
    price DECIMAL(10, 2),
    description TEXT,
    FOREIGN KEY (list_id) REFERENCES lists(id) ON DELETE CASCADE
)