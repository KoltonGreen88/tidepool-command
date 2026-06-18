# VENDORED from KoltonGreen88/idea-loss @ 2fd99051a9a7719597d8be218c08d146854c9b1e
# Single source of truth is the idea-loss repo. Edit upstream there and re-sync.
# Do NOT edit the vendored engine/ or integrations/ trees in tidepool-command.
"""ENGINE — the universal idea-loss product. Knows nothing about any customer.

Depends only on `engine.ports`. Never imports an integration, a database SDK,
a UI framework, or an LLM SDK directly. This is the IP.
"""
