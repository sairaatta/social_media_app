from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Post, User, Like
from app.schemas import PostCreate, PostResponse, CommentPermissionUpdate

import uuid

router = APIRouter(prefix="/posts", tags=["Posts"])


@router.post("/", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(
    post_data: PostCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = Post(
        user_id=current_user.id,
        title=post_data.title,
        content=post_data.content,
    )

    db.add(post)
    db.commit()
    db.refresh(post)

    return post


@router.get("/my-posts", response_model=list[PostResponse])
def get_my_posts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    posts = (
        db.query(Post)
        .filter(Post.user_id == current_user.id)
        .order_by(Post.created_at.desc())
        .all()
    )

    return posts


@router.put("/{post_id}", response_model=PostResponse)
def update_post(
    post_id: uuid.UUID,
    post_data: PostCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = (
        db.query(Post)
        .filter(
            Post.id == post_id,
            Post.user_id == current_user.id,
        )
        .first()
    )

    if post is None:
        raise HTTPException(
            status_code=404,
            detail="Post not found",
        )

    post.title = post_data.title
    post.content = post_data.content

    db.commit()
    db.refresh(post)

    return post


@router.delete("/{post_id}")
def delete_post(
    post_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = (
        db.query(Post)
        .filter(
            Post.id == post_id,
            Post.user_id == current_user.id,
        )
        .first()
    )

    if post is None:
        raise HTTPException(
            status_code=404,
            detail="Post not found",
        )

    db.delete(post)
    db.commit()

    return {"message": "Post deleted successfully"}


@router.post("/{post_id}/like")
def like_post(
    post_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = db.query(Post).filter(Post.id == post_id).first()

    if post is None:
        raise HTTPException(
            status_code=404,
            detail="Post not found",
        )

    existing_like = (
        db.query(Like)
        .filter(
            Like.user_id == current_user.id,
            Like.post_id == post_id,
        )
        .first()
    )

    if existing_like:
        return {"message": "You have already liked this post"}

    new_like = Like(
        user_id=current_user.id,
        post_id=post_id,
    )

    db.add(new_like)
    db.commit()

    return {"message": "Post liked successfully"}


@router.delete("/{post_id}/like")
def unlike_post(
    post_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = db.query(Post).filter(Post.id == post_id).first()

    if post is None:
        raise HTTPException(
            status_code=404,
            detail="Post not found",
        )

    existing_like = (
        db.query(Like)
        .filter(
            Like.user_id == current_user.id,
            Like.post_id == post_id,
        )
        .first()
    )

    if existing_like is None:
        raise HTTPException(
            status_code=404,
            detail="You have not liked this post",
        )

    db.delete(existing_like)
    db.commit()

    return {"message": "Post unliked successfully"}



@router.patch("/{post_id}/comments-permission")
def update_comments_permission(
    post_id: uuid.UUID,
    permission_data: CommentPermissionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 1. Check whether the post exists
    post = db.query(Post).filter(Post.id == post_id).first()

    if post is None:
        raise HTTPException(
            status_code=404,
            detail="Post not found",
        )

    # 2. Check whether the user is the owner or an admin
    is_post_owner = post.user_id == current_user.id
    is_admin = current_user.role == "admin"

    if not is_post_owner and not is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only the post owner or an admin can change comment permissions",
        )

    # 3. Update the permission
    post.comments_allowed = permission_data.comments_allowed

    db.commit()
    db.refresh(post)

    return {
        "message": (
            "Comments enabled successfully"
            if post.comments_allowed
            else "Comments disabled successfully"
        ),
        "post_id": str(post.id),
        "comments_allowed": post.comments_allowed,
    }


@router.get("/", response_model=list[PostResponse])
def get_all_posts(
    page: int = 1,
    limit: int = 10,
    db: Session = Depends(get_db),
):
    if page < 1:
        raise HTTPException(
            status_code=400,
            detail="Page must be at least 1",
        )

    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 100",
        )

    offset = (page - 1) * limit

    posts = (
        db.query(Post)
        .order_by(Post.created_at.desc(), Post.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return posts
