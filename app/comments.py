
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Comment, Post, User
from app.schemas import CommentCreate, CommentUpdate, CommentResponse

router = APIRouter(tags=["Comments"])


@router.post(
    "/posts/{post_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_comment(
    post_id: uuid.UUID,
    comment_data: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = db.query(Post).filter(Post.id == post_id).first()

    if post is None:
        raise HTTPException(
            status_code=404,
            detail="Post not found",
        )

    if not post.comments_allowed:
        raise HTTPException(
            status_code=403,
            detail="Comments are disabled for this post",
        )

    comment = Comment(
        post_id=post.id,
        user_id=current_user.id,
        content=comment_data.content,
    )

    db.add(comment)
    db.commit()
    db.refresh(comment)

    return comment


@router.put(
    "/comments/{comment_id}",
    response_model=CommentResponse,
)
def update_comment(
    comment_id: uuid.UUID,
    comment_data: CommentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    comment = (
        db.query(Comment)
        .filter(
            Comment.id == comment_id,
            Comment.user_id == current_user.id,
        )
        .first()
    )

    if comment is None:
        raise HTTPException(
            status_code=404,
            detail="Comment not found",
        )

    comment.content = comment_data.content

    db.commit()
    db.refresh(comment)

    return comment


@router.delete("/comments/{comment_id}")
def delete_comment(
    comment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    comment = (
        db.query(Comment)
        .filter(
            Comment.id == comment_id,
            Comment.user_id == current_user.id,
        )
        .first()
    )

    if comment is None:
        raise HTTPException(
            status_code=404,
            detail="Comment not found",
        )

    db.delete(comment)
    db.commit()

    return {"message": "Comment deleted successfully"}


@router.get("/posts/{post_id}/comments", response_model=list[CommentResponse])
def get_post_comments(
    post_id: uuid.UUID,
    page: int = 1,
    limit: int = 10,
    db: Session = Depends(get_db),
):
    # Check that the post exists
    post = db.query(Post).filter(Post.id == post_id).first()

    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")

    # Validate pagination values
    if page < 1:
        raise HTTPException(
            status_code=400,
            detail="Page must be greater than or equal to 1",
        )

    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 100",
        )

    # Calculate how many comments to skip
    skip = (page - 1) * limit

    # Fetch comments, newest first
    comments = (
        db.query(Comment)
        .filter(Comment.post_id == post_id)
        .order_by(Comment.created_at.desc(), Comment.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return comments


@router.patch("/posts/{post_id}/comments/{comment_id}/pin")
def pin_comment(
    post_id: uuid.UUID,
    comment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 1. Check whether the post exists
    post = db.query(Post).filter(Post.id == post_id).first()

    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")

    # 2. Only the post owner can pin comments
    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the post owner can pin comments",
        )

    # 3. Check whether the comment belongs to this post
    comment = (
        db.query(Comment)
        .filter(
            Comment.id == comment_id,
            Comment.post_id == post_id,
        )
        .first()
    )

    if comment is None:
        raise HTTPException(
            status_code=404,
            detail="Comment not found on this post",
        )

    # 4. Unpin any other pinned comment on this post
    other_pinned_comment = (
        db.query(Comment)
        .filter(
            Comment.post_id == post_id,
            Comment.is_pinned.is_(True),
            Comment.id != comment_id,
        )
        .first()
    )

    if other_pinned_comment is not None:
        other_pinned_comment.is_pinned = False
        db.flush()

    # 5. Pin the requested comment
    comment.is_pinned = True
    db.commit()

    return {"message": "Comment pinned successfully"}


@router.patch("/posts/{post_id}/comments/{comment_id}/unpin")
def unpin_comment(
    post_id: uuid.UUID,
    comment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 1. Check whether the post exists
    post = db.query(Post).filter(Post.id == post_id).first()

    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")

    # 2. Only the post owner can unpin comments
    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the post owner can unpin comments",
        )

    # 3. Check whether the comment belongs to this post
    comment = (
        db.query(Comment)
        .filter(
            Comment.id == comment_id,
            Comment.post_id == post_id,
        )
        .first()
    )

    if comment is None:
        raise HTTPException(
            status_code=404,
            detail="Comment not found on this post",
        )

    # 4. Unpin the requested comment
    if not comment.is_pinned:
        return {"message": "Comment is already unpinned"}

    comment.is_pinned = False
    db.commit()

    return {"message": "Comment unpinned successfully"}
