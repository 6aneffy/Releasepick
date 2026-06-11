from __future__ import annotations

import os
from typing import Any

import requests

BUFFER_ENDPOINT = "https://api.buffer.com"
_TIMEOUT = 30

MAX_CAROUSEL = 10
MAX_CAPTION_LEN = 2200


class BufferError(RuntimeError):
    pass


def _api_key() -> str:
    k = os.getenv("BUFFER_API_KEY", "")
    if not k:
        raise BufferError("BUFFER_API_KEY 누락")
    return k


def _post_graphql(query: str, variables: dict[str, Any]) -> dict[str, Any]:
    resp = requests.post(
        BUFFER_ENDPOINT,
        json={"query": query, "variables": variables},
        headers={
            "Authorization": f"Bearer {_api_key()}",
            "Content-Type": "application/json",
        },
        timeout=_TIMEOUT,
    )
    if resp.status_code >= 300:
        raise BufferError(f"HTTP {resp.status_code}: {resp.text}")
    payload = resp.json()
    if payload.get("errors"):
        raise BufferError(f"GraphQL errors: {payload['errors']}")
    return payload.get("data", {})


_CREATE_POST_MUTATION = """
mutation CreatePost($input: CreatePostInput!) {
  createPost(input: $input) {
    __typename
    ... on PostActionSuccess {
      post { id dueAt }
    }
    ... on MutationError {
      message
    }
  }
}
"""


def create_instagram_post(
    channel_id: str,
    image_urls: list[str],
    caption: str,
) -> str:
    if not channel_id:
        raise BufferError("channel_id 누락")
    if not (1 <= len(image_urls) <= MAX_CAROUSEL):
        raise BufferError(
            f"이미지 수 {len(image_urls)} — Instagram 캐러셀은 1~{MAX_CAROUSEL}장"
        )
    if len(caption) > MAX_CAPTION_LEN:
        raise BufferError(f"캡션 {len(caption)}자 > {MAX_CAPTION_LEN}자 제한")

    assets = [{"image": {"url": u}} for u in image_urls]
    variables = {
        "input": {
            "channelId": channel_id,
            "text": caption,
            "mode": "shareNow",
            "schedulingType": "automatic",
            "assets": assets,
            "metadata": {
                "instagram": {
                    "type": "post",
                    "shouldShareToFeed": True,
                }
            },
        }
    }
    data = _post_graphql(_CREATE_POST_MUTATION, variables)
    result = data.get("createPost") or {}
    typename = result.get("__typename")
    if typename == "PostActionSuccess":
        post = result.get("post") or {}
        post_id = post.get("id")
        if not post_id:
            raise BufferError(f"post.id 누락: {result}")
        return post_id
    if typename == "MutationError":
        raise BufferError(result.get("message") or "Buffer MutationError")
    raise BufferError(f"알 수 없는 응답: {result}")


def list_instagram_channels(organization_id: str) -> list[dict[str, Any]]:
    query = """
    query Channels($input: ChannelsInput!) {
      channels(input: $input) {
        id name service avatar isQueuePaused
      }
    }
    """
    data = _post_graphql(query, {"input": {"organizationId": organization_id}})
    chans = data.get("channels") or []
    return [c for c in chans if (c.get("service") or "").lower() == "instagram"]
