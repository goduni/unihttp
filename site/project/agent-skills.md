---
title: unihttp agent skills
description: Find the repository's unihttp guidance and SDK-generation skills for coding agents, with version-aware API documentation.
---

# unihttp agent skills

The repository includes two skills:

- [unihttp](https://github.com/goduni/unihttp/tree/master/.agents/skills/unihttp):
  conventions for imports, method declarations, serializers, middleware, and
  client lifecycle.
- [unihttp-client](https://github.com/goduni/unihttp/tree/master/.agents/skills/unihttp-client):
  instructions for generating a typed client package from an OpenAPI description
  or an API description.

Each skill is a directory containing a `SKILL.md` and supporting references.
Install it using your agent's supported skill mechanism. For a project-local
installation, copy the selected directories from `.agents/skills/` into the
skill directory used by your agent.

A skill is guidance for a coding agent; it is not an automatic runtime feature
of unihttp. Review generated clients against the API contract and run their
tests.

## Version-aware context

Use skills and documentation from the same revision as your library whenever
possible. Development guidance can refer to features absent from an older
release.

The published site also provides `llms.txt` and a Markdown representation of
each page under `markdown/`. These are generated from the rendered
documentation, including expanded code snippets and API reference text.
They are convenient inputs for agents, not a promise of search visibility.
