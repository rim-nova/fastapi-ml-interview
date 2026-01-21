"""
Item CRUD endpoints with pagination, filtering, search, and bulk operations.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.db.session import get_db
from app.models.item import Item, ItemStatus
from app.models.user import User
from app.schemas.item import (
    ItemCreate,
    ItemUpdate,
    ItemResponse,
    ItemListResponse,
    ItemQueryParams,
    BulkItemCreate,
    BulkDeleteRequest,
    BulkDeleteResponse,
)
from app.schemas.base import PaginatedResponse
from app.core.security import get_current_user, get_current_active_user

router = APIRouter(prefix="/items", tags=["Items"])


@router.get(
    "",
    response_model=ItemListResponse,
    summary="List items",
    description="Get paginated list of items with optional filtering."
)
async def list_items(
    # Pagination
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    # Filtering
    status: Optional[ItemStatus] = Query(None, description="Filter by status"),
    owner_id: Optional[int] = Query(None, description="Filter by owner ID"),
    # Search
    search: Optional[str] = Query(None, description="Search in title and description"),
    # Sorting
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    # Dependencies
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    List items with pagination and filtering.
    
    - **page**: Page number (starts at 1)
    - **page_size**: Number of items per page (max 100)
    - **status**: Filter by item status (active, inactive, pending, archived)
    - **owner_id**: Filter by owner (admin only, regular users see own items)
    - **search**: Search in title and description
    - **sort_by**: Field to sort by (created_at, updated_at, title)
    - **sort_order**: Sort direction (asc, desc)
    """
    # Build base query
    query = db.query(Item).filter(Item.deleted_at.is_(None))
    
    # Non-superusers can only see their own items
    if not current_user.is_superuser:
        query = query.filter(Item.owner_id == current_user.id)
    elif owner_id:
        query = query.filter(Item.owner_id == owner_id)
    
    # Apply status filter
    if status:
        query = query.filter(Item.status == status)
    
    # Apply search
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Item.title.ilike(search_term),
                Item.description.ilike(search_term)
            )
        )
    
    # Get total count
    total = query.count()
    
    # Apply sorting
    sort_column = getattr(Item, sort_by, Item.created_at)
    if sort_order == "desc":
        sort_column = sort_column.desc()
    query = query.order_by(sort_column)
    
    # Apply pagination
    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()
    
    # Calculate pagination info
    total_pages = (total + page_size - 1) // page_size
    
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
    description="Create a new item."
)
async def create_item(
    item_data: ItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a new item.
    
    The item will be owned by the current user.
    """
    db_item = Item(
        **item_data.model_dump(),
        owner_id=current_user.id
    )
    
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    
    return db_item


@router.get(
    "/{item_id}",
    response_model=ItemResponse,
    summary="Get item",
    description="Get a specific item by ID."
)
async def get_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get an item by its ID.
    
    Users can only access their own items unless they are superusers.
    """
    item = db.query(Item).filter(
        Item.id == item_id,
        Item.deleted_at.is_(None)
    ).first()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    # Check ownership
    if not current_user.is_superuser and item.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this item"
        )
    
    return item


@router.put(
    "/{item_id}",
    response_model=ItemResponse,
    summary="Update item",
    description="Update an existing item."
)
async def update_item(
    item_id: int,
    item_data: ItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update an item.
    
    Only the owner or superusers can update an item.
    """
    item = db.query(Item).filter(
        Item.id == item_id,
        Item.deleted_at.is_(None)
    ).first()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    # Check ownership
    if not current_user.is_superuser and item.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this item"
        )
    
    # Update fields
    update_data = item_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    
    db.commit()
    db.refresh(item)
    
    return item


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete item",
    description="Soft delete an item."
)
async def delete_item(
    item_id: int,
    hard_delete: bool = Query(False, description="Permanently delete (admin only)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Delete an item (soft delete by default).
    
    - Soft delete: Sets deleted_at timestamp, item can be restored
    - Hard delete: Permanently removes the item (superuser only)
    """
    item = db.query(Item).filter(Item.id == item_id).first()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    # Check ownership
    if not current_user.is_superuser and item.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this item"
        )
    
    if hard_delete:
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only superusers can permanently delete items"
            )
        db.delete(item)
    else:
        item.soft_delete()
    
    db.commit()
    return None


@router.post(
    "/bulk",
    response_model=List[ItemResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Bulk create items",
    description="Create multiple items at once."
)
async def bulk_create_items(
    bulk_data: BulkItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Create multiple items in a single request.
    
    Maximum 100 items per request.
    """
    if len(bulk_data.items) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 items per bulk create request"
        )
    
    db_items = []
    for item_data in bulk_data.items:
        db_item = Item(
            **item_data.model_dump(),
            owner_id=current_user.id
        )
        db.add(db_item)
        db_items.append(db_item)
    
    db.commit()
    for item in db_items:
        db.refresh(item)
    
    return db_items


@router.delete(
    "/bulk/delete",
    response_model=BulkDeleteResponse,
    summary="Bulk delete items",
    description="Delete multiple items at once."
)
async def bulk_delete_items(
    delete_request: BulkDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Delete multiple items by their IDs.
    
    Soft delete by default. Only owner or superuser can delete.
    """
    deleted_ids = []
    failed_ids = []
    
    for item_id in delete_request.ids:
        item = db.query(Item).filter(
            Item.id == item_id,
            Item.deleted_at.is_(None)
        ).first()
        
        if not item:
            failed_ids.append(item_id)
            continue
        
        # Check ownership
        if not current_user.is_superuser and item.owner_id != current_user.id:
            failed_ids.append(item_id)
            continue
        
        item.soft_delete()
        deleted_ids.append(item_id)
    
    db.commit()
    
    return BulkDeleteResponse(
        deleted_count=len(deleted_ids),
        deleted_ids=deleted_ids,
        failed_ids=failed_ids
    )


@router.post(
    "/{item_id}/restore",
    response_model=ItemResponse,
    summary="Restore deleted item",
    description="Restore a soft-deleted item."
)
async def restore_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Restore a soft-deleted item.
    
    Only works for items that were soft-deleted.
    """
    item = db.query(Item).filter(
        Item.id == item_id,
        Item.deleted_at.is_not(None)
    ).first()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deleted item not found"
        )
    
    # Check ownership
    if not current_user.is_superuser and item.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to restore this item"
        )
    
    item.restore()
    db.commit()
    db.refresh(item)
    
    return item
