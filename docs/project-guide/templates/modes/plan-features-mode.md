Define **what** the project does -- requirements, inputs, outputs, behavior -- without specifying **how** it is implemented. This is the source of truth for scope.

The high-level concept (why) should be captured in `concept.md`. The implementation details (how) should be written in `tech-spec.md`. The breakdown of the implementation plan (step-by-step tasks) should be written in `stories.md`.

{% include "modes/_header-sequence.md" %}

## Prerequisites

Before starting, the developer must provide (or the LLM must ask for):

1. **License preference** -- e.g. Apache-2.0, MIT, MPL-2.0, GPL-3.0. If a `LICENSE` file already exists in the project root, that license prevails.
2. **Target audience** -- CLI tool, library, web app, etc.
3. **Constraints** -- no UI, no database, must run offline, etc. (if any)

The approved `docs/specs/concept.md` must exist before starting this mode.

## Steps

1. Gather information from the developer (ask questions if needed):
   - project_name: The project name
   - programming_language: e.g., Python 3.11+, Node 22, Go 1.23
   - project_goal: One paragraph on what the project should accomplish
   - core_requirements: The essential functionality
   - operational_requirements: Error handling, logging, configuration, CLI interface, etc.
   - quality_requirements: Reliability, clarity, minimal dependencies, cross-platform, etc.
   - usability_requirements: Who uses it and how (CLI, library, web, etc.)
   - non_goals: What the project explicitly does NOT do
   - inputs: Required and optional inputs with examples (CLI args, config files, env vars)
   - outputs: File structures, console output, data formats
   - functional_requirements: Numbered list of features with behavior descriptions and edge cases
   - configuration: Config precedence, config file format/schema
   - testing_requirements: Minimum test coverage expectations
   - security_notes: Security and compliance considerations (if applicable)
   - performance_expectations: User-facing performance requirements (e.g., real-time processing, batch reports within 1 hour, response time under 200ms) (if applicable)
   - acceptance_criteria: Definition of done for the whole project

2. Generate `docs/specs/features.md` using the artifact template at `templates/artifacts/features.md`

3. Present the complete document to the developer for approval. Iterate as needed.

## Formats

### functional_requirements

```markdown
### FR-1: Feature Name

Description of the feature's purpose.

**Behavior:**
1. Step 1
2. Step 2
3. Step 3

**Edge Cases:**
- Edge case 1 -> How it's handled
- Edge case 2 -> How it's handled
```
