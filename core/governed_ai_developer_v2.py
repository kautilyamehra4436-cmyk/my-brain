"""AI Developer v2: same read-only audit with verified lessons injected."""
import json

from core.engineering_lessons_v1 import lessons_for_agent
from core.governed_ai_developer_v1 import GovernedAIDeveloperV1


class GovernedAIDeveloperV2(GovernedAIDeveloperV1):
    """Read-only auditor that receives Advait's verified engineering lessons."""

    @staticmethod
    def _prompt(sources):
        messages = GovernedAIDeveloperV1._prompt(sources)
        lessons = lessons_for_agent()
        messages[0]["content"] += (
            "\n\nVERIFIED ENGINEERING LESSONS FROM PRIOR FAILED RUNS (must apply):\n"
            + json.dumps(lessons, ensure_ascii=False, sort_keys=True)
            + "\nTreat each lesson as a mandatory review rule. Explicitly identify when "
              "a candidate issue matches a known lesson. Do not claim a legacy caller is "
              "migrated unless the supplied source proves it. Distinguish confirmed "
              "source facts from unverified runtime hypotheses."
        )
        return messages
