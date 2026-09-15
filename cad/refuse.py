"""A refusal: the pipeline will not write this, and says why.

`Refused` is raised wherever a guard fails and caught once per CLI, which
prints the reason and exits non-zero. Its OWN exception and not a
`SystemExit`, so a caller with more to do can catch a refusal and nothing
else. Its text reads `REFUSING: <reason>`, as `automation/`'s do.
"""


class Refused(Exception):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason

    def __str__(self):
        return f"REFUSING: {self.reason}"


def refuse(reason):
    raise Refused(reason)
