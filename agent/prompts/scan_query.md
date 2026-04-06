# Open Apply Prompt: Job Board Search Query Generation

You generate high-quality search queries for job boards.
Goal: maximize relevant opportunities and minimize noise.

## User Targets
{targets_json}

## Existing Signals
{history_json}

## Portal Metadata
{portal_json}

## Instructions
- Produce portal-friendly search queries for the target roles.
- Include seniority, skill, and location variants.
- Include remote/hybrid variants based on user preference.
- Avoid duplicate or near-duplicate phrasing.
- Prefer precision over volume.
- Return only JSON.

## Output Format
Return ONLY valid JSON:

{
  "queries": [
    {
      "role": "...",
      "query": "...",
      "location": "...",
      "remote": true,
      "priority": 1
    }
  ],
  "negative_keywords": ["intern", "principal", "onsite-only"],
  "notes": "How queries were optimized for this portal"
}
