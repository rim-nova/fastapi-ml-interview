// MongoDB Initialization Script
// This script runs when the MongoDB container is first created

// Switch to the application database
db = db.getSiblingDB('fastapi_db');

// Create indexes for users collection
db.users.createIndex({ "email": 1 }, { unique: true });
db.users.createIndex({ "is_deleted": 1 });
db.users.createIndex({ "created_at": 1 });

// Create indexes for items collection
db.items.createIndex({ "title": 1 });
db.items.createIndex({ "status": 1 });
db.items.createIndex({ "owner_id": 1 });
db.items.createIndex({ "is_deleted": 1 });
db.items.createIndex({ "created_at": 1 });
db.items.createIndex({ "owner_id": 1, "status": 1 });
db.items.createIndex(
    { "title": "text", "description": "text" },
    { weights: { "title": 10, "description": 5 } }
);

print("Database initialized with indexes");

// Optional: Seed initial data
// Uncomment to create initial admin user
/*
db.users.insertOne({
    email: "admin@example.com",
    hashed_password: "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.dWv.hqsqvPqJKu", // Admin123!
    full_name: "Admin User",
    is_active: true,
    is_verified: true,
    is_superuser: true,
    is_deleted: false,
    deleted_at: null,
    created_at: new Date(),
    updated_at: new Date()
});
print("Admin user created: admin@example.com");
*/
