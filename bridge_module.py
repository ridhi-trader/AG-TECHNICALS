# Thin loader — the real engine is compiled (protected), this just re-exports it.
from _bridge_core import bridge_router, add_strategy, add_license, extend_license, subscribe, unsubscribe, pause, set_ea_file, TB_HTML, DASH_HTML

# INSTALL: keep BOTH files (_bridge_core...so + this loader) in the same folder.
# Use exactly like before:
#   from bridge_module import bridge_router, add_strategy, add_license
#   app.include_router(bridge_router)
# The actual logic lives compiled inside the .so — not readable as text,
# just like the .ex5 EA file (compiled, source never shipped).
