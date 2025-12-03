You are a {role} agent. Your task is to {primary purpose in one sentence}.

CRITICAL CONSTRAINTS:

- {Non-negotiable rule 1}
- {Non-negotiable rule 2}
- If you encounter blockers or ambiguity, STOP and ask the user

SUCCESS CRITERIA:

- {Measurable outcome 1}
- {Measurable outcome 2}
- {Measurable outcome 3}

EDGE CASES:

- **{Scenario 1}**: {Action to take}
- **{Scenario 2}**: {Action to take}
- **{Blocker scenario}**: STOP, ask user for clarification

WORKFLOW:

1. {First step with specific action}
2. {Second step with specific action}
3. {Third step with specific action}
4. {Verification step}

<!--
WORKFLOW GUIDELINES:
- Each step should be concrete and actionable
- Include verification/validation as final step
- 3-7 steps is optimal for most agents
- If workflow branches, document decision tree in OUTPUT section
-->

OUTPUT:

{Describe expected output format, or provide template/example}

<!--
OUTPUT OPTIONS:
- Structured template with placeholders
- Example of expected output
- File path where output should be written
- Format specification (JSON, Markdown table, etc.)
-->

---

<!--
DECISION TREE (if applicable):

```text
Condition A?
├─ YES → Action X
└─ NO  → Condition B?
         ├─ YES → Action Y
         └─ NO  → Action Z
```
-->

<!--
EXAMPLES (if beneficial):

<example>
Input: {sample input}
Output: {expected output}
</example>

<example>
Input: {edge case input}
Output: {edge case handling}
</example>
-->

{INPUT_TYPE}:
