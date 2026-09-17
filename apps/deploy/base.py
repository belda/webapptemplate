from django.core.management.base import BaseCommand


class PostDeployCommand(BaseCommand):
    """A management command that the deploy runs once, after the release is live.

    Subclass it and set ``post_deploy_id`` to a unique, sortable id — the
    convention is ``<YYYYMMDD>_<what_it_does>``, so the run order is the order
    the steps were written. Steps must not depend on each other; the ordering
    exists so two hosts run them the same way, not to express a dependency.

    The command stays an ordinary management command: runnable by hand, with its
    own arguments, and safe to run twice. ``post_deploy`` is only what makes the
    system remember it ran.
    """

    post_deploy_id: str = ""
