"""
MongoDB Database Connection.

Uses Motor (async MongoDB driver) for non-blocking operations.
Provides connection management and database access.
"""
import logging
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure

from app.config import settings

logger = logging.getLogger(__name__)


class MongoDB:
    """
    MongoDB connection manager.
    
    Usage:
        # In lifespan
        await mongodb.connect()
        yield
        await mongodb.close()
        
        # In endpoints
        db = mongodb.get_database()
        await db.users.find_one({"email": email})
    """
    
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None
    
    async def connect(self) -> None:
        """
        Connect to MongoDB.
        
        Initializes the Motor client and database reference.
        """
        logger.info(f"Connecting to MongoDB at {settings.MONGODB_URL}")
        
        try:
            self.client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                minPoolSize=settings.MONGODB_MIN_POOL_SIZE,
                maxPoolSize=settings.MONGODB_MAX_POOL_SIZE,
                maxIdleTimeMS=settings.MONGODB_MAX_IDLE_TIME_MS,
            )
            
            # Verify connection
            await self.client.admin.command('ping')
            
            self.db = self.client[settings.MONGODB_DB_NAME]
            
            # Create indexes
            await self._create_indexes()
            
            logger.info(f"Connected to MongoDB database: {settings.MONGODB_DB_NAME}")
            
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    async def close(self) -> None:
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
    
    def get_database(self) -> AsyncIOMotorDatabase:
        """
        Get the database instance.
        
        Returns:
            AsyncIOMotorDatabase instance
            
        Raises:
            RuntimeError: If database is not connected
        """
        if self.db is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self.db
    
    async def _create_indexes(self) -> None:
        """Create database indexes for optimal query performance."""
        if self.db is None:
            return
        
        # Users collection indexes
        await self.db.users.create_index("email", unique=True)
        await self.db.users.create_index("is_deleted")
        await self.db.users.create_index("created_at")
        
        # Items collection indexes
        await self.db.items.create_index("title")
        await self.db.items.create_index("status")
        await self.db.items.create_index("owner_id")
        await self.db.items.create_index("is_deleted")
        await self.db.items.create_index("created_at")
        
        # Compound indexes
        await self.db.items.create_index([("owner_id", 1), ("status", 1)])
        await self.db.items.create_index([("title", "text"), ("description", "text")])
        
        logger.info("Database indexes created")


# Global MongoDB instance
mongodb = MongoDB()


async def get_database() -> AsyncIOMotorDatabase:
    """
    Dependency for getting database in endpoints.
    
    Usage:
        @app.get("/users")
        async def get_users(db: AsyncIOMotorDatabase = Depends(get_database)):
            users = await db.users.find().to_list(100)
            return users
    """
    return mongodb.get_database()
