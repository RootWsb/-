"""Production-facing sidecar service for SkillRouter inference."""

__all__ = ["RouterRuntime", "RouterSettings", "create_app"]


def __getattr__(name):
    if name in __all__:
        from .app import RouterRuntime, RouterSettings, create_app

        exports = {
            "RouterRuntime": RouterRuntime,
            "RouterSettings": RouterSettings,
            "create_app": create_app,
        }
        return exports[name]
    raise AttributeError(name)
