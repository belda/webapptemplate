from webapptemplate.apps.deploy.base import PostDeployCommand

runs = []


class Command(PostDeployCommand):
    help = "Test step that succeeds."
    post_deploy_id = "20990101_step_ok"

    def handle(self, *args, **options):
        runs.append(self.post_deploy_id)
        self.stdout.write("ok step said something")
