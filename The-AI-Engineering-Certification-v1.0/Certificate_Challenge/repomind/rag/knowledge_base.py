from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from .types import Chunk

# Resolve the data directory relative to this file rather than the process
# working directory, so it works regardless of where the code is invoked from
# (local `python`, `vercel dev`, or a Vercel Python Function where cwd differs).
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
LINK_RE = re.compile(r"(?:PR#\d+|[A-Z]+-\d+|RFC-\d+|PROP-\d+)")


def _load_json(name: str) -> list[dict[str, Any]]:
    with (DATA_DIR / name).open("r", encoding="utf-8") as file:
        return json.load(file)


def _extract_linked_ids(text: str, extra_ids: list[str] | None = None) -> list[str]:
    ids = LINK_RE.findall(text or "")
    if extra_ids:
        ids.extend(extra_ids)
    return list(dict.fromkeys(ids))


@lru_cache(maxsize=1)
def build_knowledge_base() -> tuple[Chunk, ...]:
    chunks: list[Chunk] = []

    for commit in _load_json("commits.json"):
        pr_number = commit.get("pr_number")
        pr_ref = [f"PR#{pr_number}"] if pr_number else []
        files_changed = commit.get("files_changed", [])
        chunks.append(
            Chunk(
                id=f"commit:{commit['sha']}",
                type="commit",
                text="\n".join(
                    [
                        f"Commit {commit['sha']} by {commit['author']} on {commit['date']}:",
                        commit["message"],
                        f"Files changed: {', '.join(files_changed)}",
                        f"Part of PR #{pr_number}"
                        if pr_number
                        else "(no PR - undocumented change, no linked ticket)",
                    ]
                ),
                metadata={
                    "author": commit.get("author"),
                    "date": commit.get("date"),
                    "files": files_changed,
                    "linkedIds": _extract_linked_ids(commit.get("message", ""), pr_ref),
                },
            )
        )

    for pr in _load_json("pull_requests.json"):
        comments = pr.get("review_comments", [])
        review_text = (
            "\n".join(
                f"  @{comment['author']} [{comment['created_at'][:10]}]: {comment['body']}"
                for comment in comments
            )
            if comments
            else "  (no review comments)"
        )
        linked_ticket = pr.get("linked_ticket")
        linked_ids = _extract_linked_ids(
            f"{pr.get('description', '')} {pr.get('title', '')}",
            [linked_ticket] if linked_ticket else [],
        )
        files_changed = pr.get("files_changed", [])
        chunks.append(
            Chunk(
                id=f"PR#{pr['number']}",
                type="pr",
                text="\n".join(
                    [
                        f"PR #{pr['number']}: {pr['title']}",
                        f"Author: {pr['author']} | Merged: {pr['merged_at']} | Linked ticket: {linked_ticket or 'none'}",
                        "",
                        "Description:",
                        pr["description"],
                        "",
                        "Review discussion:",
                        review_text,
                        "",
                        f"Files changed: {', '.join(files_changed)}",
                    ]
                ),
                metadata={
                    "author": pr.get("author"),
                    "date": pr.get("merged_at"),
                    "title": pr.get("title"),
                    "linkedIds": linked_ids,
                    "files": files_changed,
                },
            )
        )

    for ticket in _load_json("tickets.json"):
        comments = ticket.get("comments", [])
        comments_text = (
            "\n".join(
                f"  @{comment['author']} [{comment['created_at'][:10]}]: {comment['body']}"
                for comment in comments
            )
            if comments
            else "  (no comments)"
        )
        comment_blob = " ".join(comment.get("body", "") for comment in comments)
        chunks.append(
            Chunk(
                id=ticket["id"],
                type="ticket",
                text="\n".join(
                    [
                        f"Ticket {ticket['id']}: {ticket['title']}",
                        f"Status: {ticket['status']} | Created: {ticket['created_at']}",
                        "",
                        "Description:",
                        ticket["description"],
                        "",
                        "Comments:",
                        comments_text,
                    ]
                ),
                metadata={
                    "title": ticket.get("title"),
                    "date": ticket.get("created_at"),
                    "linkedIds": _extract_linked_ids(f"{ticket.get('description', '')} {comment_blob}"),
                },
            )
        )

    threads: dict[str, list[dict[str, Any]]] = {}
    for message in _load_json("chat_messages.json"):
        threads.setdefault(message["thread_id"], []).append(message)

    for thread_id, messages in threads.items():
        channel = messages[0]["channel"]
        messages_text = "\n".join(
            f"  [{message['timestamp'][:10]}] @{message['author']}: {message['text']}"
            for message in messages
        )
        all_text = " ".join(message.get("text", "") for message in messages)
        chunks.append(
            Chunk(
                id=f"chat:{thread_id}",
                type="chat",
                text=f"Chat thread {thread_id} in {channel}:\n{messages_text}",
                metadata={
                    "date": messages[0].get("timestamp"),
                    "linkedIds": _extract_linked_ids(all_text),
                },
            )
        )

    for email in _load_json("emails.json"):
        chunks.append(
            Chunk(
                id=f"email:{email['thread_id']}",
                type="email",
                text="\n".join(
                    [
                        f"Email: {email['subject']}",
                        f"From: {email['from']} | To: {', '.join(email['to'])} | Date: {email['date']}",
                        "",
                        email["body"],
                    ]
                ),
                metadata={
                    "author": email.get("from"),
                    "date": email.get("date"),
                    "title": email.get("subject"),
                    "linkedIds": _extract_linked_ids(email.get("body", "")),
                },
            )
        )

    for doc in _load_json("docs.json"):
        chunks.append(
            Chunk(
                id=doc["doc_id"],
                type="doc",
                text="\n".join(
                    [
                        f"Document {doc['doc_id']}: {doc['title']}",
                        f"Status: {doc['status']} | Last updated: {doc['last_updated']}",
                        "",
                        doc["content"],
                    ]
                ),
                metadata={
                    "title": doc.get("title"),
                    "date": doc.get("last_updated"),
                    "linkedIds": _extract_linked_ids(doc.get("content", "")),
                },
            )
        )

    return tuple(chunks)
