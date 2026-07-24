# Disambiguation Stage Prompt Template

Perform only project identity disambiguation for the supplied generation request. Do not research a full case package, download images, write `case.md`, write `case.json`, or claim that a project is confirmed without sufficient identifying signals.

Return exactly one JSON object matching the supplied `disambiguation_result` schema.

- Keep `job_id` identical to the input request.
- Return `identity_confirmed` only when the project identity is clear from the request itself; otherwise return `confirmation_required`.
- Give one to five concrete candidate projects. Use empty `source_urls` when this minimal stage has no verified URLs rather than inventing links.
- Use `high`, `medium`, or `low` confidence. Preserve uncertainty in `confirmation_question`.
- Do not run a full source-sufficiency decision in this stage. The later research worker owns source collection and verification.
