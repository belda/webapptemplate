from webapptemplate.apps.deploy.base import PostDeployCommand

runs = []


class Command(PostDeployCommand):
    help = "Test step that raises."
    post_deploy_id = "20990102_step_fail"

    def handle(self, *args, **options):
        runs.append(self.post_deploy_id)
        self.stdout.write("got as far as this")
        raise RuntimeError("the backfill hit real data")
