# VENDORED from KoltonGreen88/idea-loss @ 9bb48b5bc6a07e4c55c11eee7fd2e043eafeb985
# Single source of truth is the idea-loss repo. Edit upstream there and re-sync.
# Do NOT edit the vendored engine/ or integrations/ trees in tidepool-command.
"""ENGINE — the universal idea-loss product. Knows nothing about any customer.

Depends only on `engine.ports`. Never imports an integration, a database SDK,
a UI framework, or an LLM SDK directly. This is the IP.
"""
