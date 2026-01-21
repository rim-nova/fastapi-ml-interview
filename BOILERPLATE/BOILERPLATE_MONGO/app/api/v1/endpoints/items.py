"""
Item CRUD endpoints for MongoDB.
"""
from datetime import datetime
from typing import Optional, List

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongodb import get_database
from app.models.item import ItemStatus, ItemPriority
from app.schemas.item import (
    ItemCreate,
    ItemUpdate,
    ItemResponse,
    ItemListResponse,
    BulkItemCreate,
    BulkDeleteRequest,
    BulkDeleteResponse,
)
from app.core.security import get_current_user, get_current_active_user

router = APIRouter(prefix="/items", tags=["Items"])


def item_to_response(item: dict) -> dict:
    """Convert MongoDB document to response format."""
    if item and "_id" in item:
        item["_id"] = str(item["_id"])
    return item


@router.get(
    "",
    response_model=ItemListResponse,
    summary="List items",
)
async def list_items(
    # Pagination
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    # Filtering
    status: Optional[ItemStatus] = Query(None, description="Filter by status"),
    priority: Optional[ItemPriority] = Query(None, description="Filter by priority"),
    # Search
    search: Optional[str] = Query(None, description="Search in title and description"),
    # Sorting
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    # Dependencies
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(get_current_active_user),
):
    """List items with pagination and filtering."""
    # Build query filter
    query_filter = {"is_deleted": False}
    
    # Non-superusers can only see their own items
    if not current_user.get("is_superuser", False):
        query_filter["owner_id"] = str(current_user["_id"])
    
    # Apply status filter
    if status:
        query_filter["status"] = status.value
    
    # Apply priority filter
    if priority:
        query_filter["priority"] = priority.value
    
    # Apply text search
    if search:
        query_filter["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}}
        ]
    
    # Get total count
    total = await db.items.count_documents(query_filter)
    
    # Build sort
    sort_direction = -1 if sort_order == "desc" else 1
    sort_spec = [(sort_by, sort_direction)]
    
    # Apply pagination
    skip = (page - 1) * page_size
    
    # Execute query
    cursor = db.items.find(query_filter).sort(sort_spec).skip(skip).limit(page_size)
    items = await cursor.to_list(length=page_size)
    
    # Convert ObjectIds to strings
    items = [item_to_response(item) for item in items]
    
    # Calculate pagination info
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    
    return ItemListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1
    )


@router.post(
    "",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create item",
)
async def create_item(
    item_data: ItemCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(get_current_active_user),
):
    """Create a new item."""
    # Build item document
    item_doc = {
        **item_data.model_dump(),
        "owner_id": str(current_user["_id"]),
        "is_deleted": False,
        "deleted_at": None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    # Convert enums to strings
    if "status" in item_doc and hasattr(item_doc["status"], "value"):
        item_doc["status"] = item_doc["status"].value
    if "priority" in item_doc and hasattr(item_doc["priority"], "value"):
        item_doc["priority"] = item_doc["priority"].value
    
    result = await db.items.insert_one(item_doc)
    item_doc["_id"] = str(result.inserted_id)
    
    return item_doc


@router.get(
    "/{item_id}",
    response_model=ItemResponse,
    summary="Get item",
)
async def get_item(
    item_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(get_current_active_user),
):
    """Get an item by its ID."""
    try:
        item = await db.items.find_one({
            "_id": ObjectId(item_id),
            "is_deleted": False
        })
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid item ID"
        )
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    # Check ownership
    if not current_user.get("is_superuser", False) and item.get("owner_id") != str(current_user["_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this item"
        )
    
    return item_to_response(item)


@router.put(
    "/{item_id}",
    response_model=ItemResponse,
    summary="Update item",
)
async def update_item(
    item_id: str,
    item_data: ItemUpdate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(get_current_active_user),
):
    """Update an item."""
    try:
        item = await db.items.find_one({
            "_id": ObjectId(item_id),
            "is_deleted": False
        })
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid item ID"
        )
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    # Check ownership
    if not current_user.get("is_superuser", False) and item.get("owner_id") != str(current_user["_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this item"
        )
    
    # Build update document
    update_data = item_data.model_dump(exclude_unset=True)
    
    # Convert enums to strings
    if "status" in update_data and hasattr(update_data["status"], "value"):
        update_data["status"] = update_data["status"].value
    if "priority" in update_data and hasattr(update_data["priority"], "value"):
        update_data["priority"] = update_data["priority"].value
    
    update_data["updated_at"] = datetime.utcnow()
    
    await db.items.update_one(
        {"_id": ObjectId(item_id)},
        {"$set": update_data}
    )
    
    # Get updated item
    updated_item = await db.items.find_one({"_id": ObjectId(item_id)})
    return item_to_response(updated_item)


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete item",
)
async def delete_item(
    item_id: str,
    hard_delete: bool = Query(False, description="Permanently delete (admin only)"),
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(get_current_active_user),
):
    """Delete an item (soft delete by default)."""
    try:
        item = await db.items.find_one({"_id": ObjectId(item_id)})
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid item ID"
        )
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    # Check ownership
    if not current_user.get("is_superuser", False) and item.get("owner_id") != str(current_user["_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this item"
        )
    
    if hard_delete:
        if not current_user.get("is_superuser", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only superusers can permanently delete items"
            )
        await db.items.delete_one({"_id": ObjectId(item_id)})
    else:
        # Soft delete
        await db.items.update_one(
            {"_id": ObjectId(item_id)},
            {"$set": {
                "is_deleted": True,
                "deleted_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }}
        )
    
    return None


@router.post(
    "/bulk",
    response_model=List[ItemResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Bulk create items",
)
async def bulk_create_items(
    bulk_data: BulkItemCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(get_current_active_user),
):
    """Create multiple items in a single request."""
    if len(bulk_data.items) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 items per bulk create request"
        )
    
    items_to_insert = []
    for item_data in bulk_data.items:
        item_doc = {
            **item_data.model_dump(),
            "owner_id": str(current_user["_id"]),
            "is_deleted": False,
            "deleted_at": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        # Convert enums
        if "status" in item_doc and hasattr(item_doc["status"], "value"):
            item_doc["status"] = item_doc["status"].value
        if "priority" in item_doc and hasattr(item_doc["priority"], "value"):
            item_doc["priority"] = item_doc["priority"].value
        items_to_insert.append(item_doc)
    
    result = await db.items.insert_many(items_to_insert)
    
    # Get inserted items
    inserted_items = await db.items.find({
        "_id": {"$in": result.inserted_ids}
    }).to_list(length=len(result.inserted_ids))
    
    return [item_to_response(item) for item in inserted_items]


@router.delete(
    "/bulk/delete",
    response_model=BulkDeleteResponse,
    summary="Bulk delete items",
)
async def bulk_delete_items(
    delete_request: BulkDeleteRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(get_current_active_user),
):
    """Delete multiple items by their IDs (soft delete)."""
    deleted_ids = []
    failed_ids = []
    
    for item_id in delete_request.ids:
        try:
            item = await db.items.find_one({
                "_id": ObjectId(item_id),
                "is_deleted": False
            })
            
            if not item:
                failed_ids.append(item_id)
                continue
            
            # Check ownership
            if not current_user.get("is_superuser", False) and item.get("owner_id") != str(current_user["_id"]):
                failed_ids.append(item_id)
                continue
            
            # Soft delete
            await db.items.update_one(
                {"_id": ObjectId(item_id)},
                {"$set": {
                    "is_deleted": True,
                    "deleted_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }}
            )
            deleted_ids.append(item_id)
            
        except Exception:
            failed_ids.append(item_id)
    
    return BulkDeleteResponse(
        deleted_count=len(deleted_ids),
        deleted_ids=deleted_ids,
        failed_ids=failed_ids
    )


@router.post(
    "/{item_id}/restore",
    response_model=ItemResponse,
    summary="Restore deleted item",
)
async def restore_item(
    item_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(get_current_active_user),
):
    """Restore a soft-deleted item."""
    try:
        item = await db.items.find_one({
            "_id": ObjectId(item_id),
            "is_deleted": True
        })
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid item ID"
        )
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deleted item not found"
        )
    
    # Check ownership
    if not current_user.get("is_superuser", False) and item.get("owner_id") != str(current_user["_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to restore this item"
        )
    
    await db.items.update_one(
        {"_id": ObjectId(item_id)},
        {"$set": {
            "is_deleted": False,
            "deleted_at": None,
            "updated_at": datetime.utcnow()
        }}
    )
    
    restored_item = await db.items.find_one({"_id": ObjectId(item_id)})
    return item_to_response(restored_item)


@router.get(
    "/search/text",
    response_model=ItemListResponse,
    summary="Full-text search items",
)
async def search_items_text(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(get_current_active_user),
):
    """
    Full-text search across items.
    
    Uses MongoDB text index on title and description.
    """
    query_filter = {
        "$text": {"$search": q},
        "is_deleted": False
    }
    
    # Non-superusers can only see their own items
    if not current_user.get("is_superuser", False):
        query_filter["owner_id"] = str(current_user["_id"])
    
    # Get total count
    total = await db.items.count_documents(query_filter)
    
    # Apply pagination with text score sorting
    skip = (page - 1) * page_size
    
    cursor = db.items.find(
        query_filter,
        {"score": {"$meta": "textScore"}}
    ).sort([("score", {"$meta": "textScore"})]).skip(skip).limit(page_size)
    
    items = await cursor.to_list(length=page_size)
    items = [item_to_response(item) for item in items]
    
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    
    return ItemListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1
    )
