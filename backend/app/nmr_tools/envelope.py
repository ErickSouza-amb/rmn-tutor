TOOLS_VERSION = "1"


def ok(tool: str, data, warnings: list[str] | None = None, limitations: list[str] | None = None) -> dict:
    return {
        "ok": True,
        "tool": tool,
        "version": TOOLS_VERSION,
        "data": data,
        "warnings": warnings or [],
        "limitations": limitations or [],
    }


def not_available(tool: str, reason: str, limitations: list[str] | None = None) -> dict:
    return ok(tool, {"status": "not_available", "reason": reason}, limitations=limitations)


def error(tool: str, code: str, message: str) -> dict:
    return {
        "ok": False,
        "tool": tool,
        "version": TOOLS_VERSION,
        "error": {"code": code, "message": message},
        "warnings": [],
        "limitations": [],
    }
