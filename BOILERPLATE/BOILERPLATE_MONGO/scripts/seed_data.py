#!/usr/bin/env python3
"""
MongoDB Database Seed Script.

Creates sample data for development and testing.

Usage:
    python scripts/seed_data.py

Test Accounts (after seeding):
    - admin@example.com / Admin123! (superuser)
    - user@example.com / User123!
    - test@example.com / Test123!
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
from app.core.security import get_password_hash


async def seed_users(db):
    """Create sample users."""
    users_data = [
        {
            "email": "admin@example.com",
            "password": "Admin123!",
            "full_name": "Admin User",
            "is_superuser": True,
            "is_verified": True,
        },
        {
            "email": "user@example.com",
            "password": "User123!",
            "full_name": "Regular User",
            "is_superuser": False,
            "is_verified": True,
        },
        {
            "email": "test@example.com",
            "password": "Test123!",
            "full_name": "Test User",
            "is_superuser": False,
            "is_verified": False,
        },
    ]
    
    created_users = []
    for user_data in users_data:
        # Check if user exists
        existing = await db.users.find_one({"email": user_data["email"]})
        if existing:
            print(f"User {user_data['email']} already exists, skipping...")
            created_users.append(existing)
            continue
        
        user_doc = {
            "email": user_data["email"],
            "hashed_password": get_password_hash(user_data["password"]),
            "full_name": user_data["full_name"],
            "is_superuser": user_data["is_superuser"],
            "is_verified": user_data["is_verified"],
            "is_active": True,
            "is_deleted": False,
            "deleted_at": None,
            "avatar_url": None,
            "bio": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        
        result = await db.users.insert_one(user_doc)
        user_doc["_id"] = result.inserted_id
        created_users.append(user_doc)
        print(f"Created user: {user_data['email']}")
    
    return created_users


async def seed_items(db, users):
    """Create sample items."""
    if not users:
        print("No users available for item ownership")
        return
    
    items_data = [
        {
            "title": "Complete Project Setup",
            "description": "Set up the development environment and project structure",
            "status": "completed",
            "priority": "high",
            "price": 0.0,
            "quantity": 1,
            "metadata": {"category": "setup", "estimated_hours": 4},
            "tags": ["setup", "devops"],
        },
        {
            "title": "Implement User Authentication",
            "description": "Add JWT-based authentication with login, register, and token refresh",
            "status": "active",
            "priority": "urgent",
            "price": 150.00,
            "quantity": 1,
            "metadata": {"category": "security", "estimated_hours": 8},
            "tags": ["security", "auth", "jwt"],
        },
        {
            "title": "Design Database Schema",
            "description": "Create the initial database schema with all required collections",
            "status": "completed",
            "priority": "high",
            "price": 200.00,
            "quantity": 1,
            "metadata": {"category": "database", "estimated_hours": 6},
            "tags": ["database", "mongodb", "schema"],
        },
        {
            "title": "Write API Documentation",
            "description": "Document all API endpoints with examples and response schemas",
            "status": "pending",
            "priority": "medium",
            "price": 75.00,
            "quantity": 1,
            "metadata": {"category": "documentation", "estimated_hours": 4},
            "tags": ["docs", "api"],
        },
        {
            "title": "Set Up CI/CD Pipeline",
            "description": "Configure GitHub Actions for automated testing and deployment",
            "status": "draft",
            "priority": "low",
            "price": 0.0,
            "quantity": 1,
            "metadata": {"category": "devops", "estimated_hours": 3},
            "tags": ["devops", "ci", "automation"],
        },
        {
            "title": "Product A - Premium Widget",
            "description": "High-quality premium widget with advanced features",
            "status": "active",
            "priority": "medium",
            "price": 99.99,
            "quantity": 50,
            "metadata": {"category": "product", "sku": "WIDGET-001"},
            "tags": ["product", "premium"],
        },
        {
            "title": "Product B - Basic Gadget",
            "description": "Entry-level gadget for beginners",
            "status": "active",
            "priority": "low",
            "price": 29.99,
            "quantity": 100,
            "metadata": {"category": "product", "sku": "GADGET-001"},
            "tags": ["product", "basic"],
        },
        {
            "title": "Archived Task",
            "description": "This is an archived item for testing",
            "status": "archived",
            "priority": "low",
            "price": 0.0,
            "quantity": 0,
            "metadata": {"archived_reason": "completed project"},
            "tags": ["archived"],
        },
    ]
    
    # Distribute items among users
    for i, item_data in enumerate(items_data):
        owner = users[i % len(users)]
        
        # Check if item exists
        existing = await db.items.find_one({"title": item_data["title"]})
        if existing:
            print(f"Item '{item_data['title']}' already exists, skipping...")
            continue
        
        item_doc = {
            **item_data,
            "owner_id": str(owner["_id"]),
            "is_deleted": False,
            "deleted_at": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        
        await db.items.insert_one(item_doc)
        print(f"Created item: {item_data['title']} (owner: {owner['email']})")


async def main():
    """Run the seed script."""
    print("=" * 50)
    print("Starting MongoDB seed...")
    print("=" * 50)
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB_NAME]
    
    try:
        # Verify connection
        await client.admin.command('ping')
        print(f"\nConnected to MongoDB: {settings.MONGODB_DB_NAME}")
        
        # Seed users
        print("\n--- Seeding Users ---")
        users = await seed_users(db)
        
        # Seed items
        print("\n--- Seeding Items ---")
        await seed_items(db, users)
        
        print("\n" + "=" * 50)
        print("MongoDB seeding completed successfully!")
        print("=" * 50)
        print("\nTest credentials:")
        print("  admin@example.com / Admin123! (superuser)")
        print("  user@example.com / User123!")
        print("  test@example.com / Test123!")
        
    except Exception as e:
        print(f"\nError during seeding: {e}")
        raise
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
