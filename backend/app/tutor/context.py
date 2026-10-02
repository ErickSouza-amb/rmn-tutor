import base64

IMAGE_MARKER = {"type": "rmn_image_ref"}


def has_image_marker(content) -> bool:
    return isinstance(content, list) and any(isinstance(b, dict) and b.get("type") == "rmn_image_ref" for b in content)


def build_api_messages(rows, image: tuple[bytes, str] | None) -> list[dict]:
    messages: list[dict] = []
    for row in rows:
        if row.role == "system":
            messages.append({"role": "system", "content": row.content})
            continue
        content = row.content
        if isinstance(content, list) and has_image_marker(content):
            blocks = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "rmn_image_ref":
                    if image is not None:
                        data, media_type = image
                        blocks.append(
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": base64.standard_b64encode(data).decode("ascii"),
                                },
                            }
                        )
                else:
                    blocks.append(block)
            content = blocks
        messages.append({"role": row.role, "content": content})
    return messages
