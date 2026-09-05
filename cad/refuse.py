"""A refusal: the pipeline will not write this, and says why.

`Refused` is raised wherever a guard fails — a part not built, a plate with
no home for its tower, a project MakerWorld would reject, a `--game` nobody
has heard of — and caught once per CLI, which prints the reason and exits
non-zero. It is its own exception and not a `SystemExit` so that a caller
with more to do (the catalogue loop in `cad.cascade`, the tests) can catch a
refusal and nothing else. Its text reads `REFUSING: <reason>`, as every
refusal in `automation/` does.
"""


class Refused(Exception):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason

    def __str__(self):
        return f"REFUSING: {self.reason}"


def refuse(reason):
    raise Refused(reason)
