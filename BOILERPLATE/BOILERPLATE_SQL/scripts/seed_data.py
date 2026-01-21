#!/usr/bin/env python3
"""
Database Seed Script.

Creates sample data for development and testing.

Usage:
    python scripts/seed_data.py

Test Accounts (after seeding):
    - admin@example.com / Admin123! (superuser)
    - user@example.com / User123!
    - test@example.com / Test123!
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal, create_tables
from app.models.user import User
from app.models.item import Item, ItemStatus, ItemPriority
from app.core.security import get_password_hash


def seed_users(db):
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
        existing = db.query(User).filter(User.email == user_data["email"]).first()
        if existing:
            print(f"User {user_data['email']} already exists, skipping...")
            created_users.append(existing)
            continue
        
        user = User(
            email=user_data["email"],
            hashed_password=get_password_hash(user_data["password"]),
            full_name=user_data["full_name"],
            is_superuser=user_data["is_superuser"],
            is_verified=user_data["is_verified"],
            is_active=True,
        )
        db.add(user)
        created_users.append(user)
        print(f"Created user: {user_data['email']}")
    
    db.commit()
    return created_users


def seed_items(db, users):
    """Create sample items."""
    if not users:
        print("No users available for item ownership")
        return
    
    items_data = [
        {
            "title": "Complete Project Setup",
            "description": "Set up the development environment and project structure",
            "status": ItemStatus.COMPLETED,
            "priority": ItemPriority.HIGH,
            "price": 0.0,
            "quantity": 1,
            "metadata": {"category": "setup", "estimated_hours": 4},
        },
        {
            "title": "Implement User Authentication",
            "description": "Add JWT-based authentication with login, register, and token refresh",
            "status": ItemStatus.ACTIVE,
            "priority": ItemPriority.URGENT,
            "price": 150.00,
            "quantity": 1,
            "metadata": {"category": "security", "estimated_hours": 8},
        },
        {
            "title": "Design Database Schema",
            "description": "Create the initial database schema with all required tables and relationships",
            "status": ItemStatus.COMPLETED,
            "priority": ItemPriority.HIGH,
            "price": 200.00,
            "quantity": 1,
            "metadata": {"category": "database", "estimated_hours": 6},
        },
        {
            "title": "Write API Documentation",
            "description": "Document all API endpoints with examples and response schemas",
            "status": ItemStatus.PENDING,
            "priority": ItemPriority.MEDIUM,
            "price": 75.00,
            "quantity": 1,
            "metadata": {"category": "documentation", "estimated_hours": 4},
        },
        {
            "title": "Set Up CI/CD Pipeline",
            "description": "Configure GitHub Actions for automated testing and deployment",
            "status": ItemStatus.DRAFT,
            "priority": ItemPriority.LOW,
            "price": 0.0,
            "quantity": 1,
            "metadata": {"category": "devops", "estimated_hours": 3},
        },
        {
            "title": "Product A - Premium Widget",
            "description": "High-quality premium widget with advanced features",
            "status": ItemStatus.ACTIVE,
            "priority": ItemPriority.MEDIUM,
            "price": 99.99,
            "quantity": 50,
            "metadata": {"category": "product", "sku": "WIDGET-001"},
        },
        {
            "title": "Product B - Basic Gadget",
            "description": "Entry-level gadget for beginners",
            "status": ItemStatus.ACTIVE,
            "priority": ItemPriority.LOW,
            "price": 29.99,
            "quantity": 100,
            "metadata": {"category": "product", "sku": "GADGET-001"},
        },
        {
            "title": "Archived Task",
            "description": "This is an archived item for testing",
            "status": ItemStatus.ARCHIVED,
            "priority": ItemPriority.LOW,
            "price": 0.0,
            "quantity": 0,
            "metadata": {"archived_reason": "completed project"},
        },
    ]
    
    # Distribute items among users
    for i, item_data in enumerate(items_data):
        owner = users[i % len(users)]
        
        # Check if item exists
        existing = db.query(Item).filter(Item.title == item_data["title"]).first()
        if existing:
            print(f"Item '{item_data['title']}' already exists, skipping...")
            continue
        
        item = Item(
            **item_data,
            owner_id=owner.id
        )
        db.add(item)
        print(f"Created item: {item_data['title']} (owner: {owner.email})")
    
    db.commit()


def main():
    """Run the seed script."""
    print("=" * 50)
    print("Starting database seed...")
    print("=" * 50)
    
    # Create tables if they don't exist
    create_tables()
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Seed users
        print("\n--- Seeding Users ---")
        users = seed_users(db)
        
        # Seed items
        print("\n--- Seeding Items ---")
        seed_items(db, users)
        
        print("\n" + "=" * 50)
        print("Database seeding completed successfully!")
        print("=" * 50)
        print("\nTest credentials:")
        print("  admin@example.com / Admin123! (superuser)")
        print("  user@example.com / User123!")
        print("  test@example.com / Test123!")
        
    except Exception as e:
        print(f"\nError during seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
