"""Cloud configuration the scan does not read (benchmark section 20): when a project carries Terraform,
CloudFormation or Helm files, `aix code security` says how many and which Checkov command reads them; a project
without them gets no such line. The scan stays silent about nothing."""
import unittest

from helpers import install, project_cmd, temp_home


class CloudConfig(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self); self.project = self.home / "app"
        (self.project / "src").mkdir(parents=True); (self.project / "src/app.py").write_text("x = 1\n")
        install(self.home, self.project)

    def test_present_files_are_counted_and_named(self):
        (self.project / "infra/modules/db").mkdir(parents=True)
        (self.project / "infra/main.tf").write_text('resource "aws_s3_bucket" "b" {}\n')
        (self.project / "infra/modules/db/rds.tf").write_text('resource "aws_db_instance" "d" {}\n')
        (self.project / "infra/vars.tfvars").write_text('region = "eu-west-1"\n')
        (self.project / "infra/stack.yaml").write_text("AWSTemplateFormatVersion: '2010-09-09'\nResources:\n  B:\n    Type: AWS::S3::Bucket\n")
        (self.project / "chart/templates").mkdir(parents=True); (self.project / "chart/Chart.yaml").write_text("apiVersion: v2\nname: app\n")
        out = project_cmd(self.project, self.home, "code", "security", check=False).stdout
        self.assertIn("not read by this scan: 3 Terraform files (run `checkov -d . --framework terraform`)", out, out)
        self.assertIn("1 CloudFormation template (run `checkov -d . --framework cloudformation`)", out, out)
        self.assertIn("1 Helm chart (run `checkov -d . --framework helm`, needs `helm`)", out, out)

    def test_nothing_to_say_without_them(self):
        (self.project / "k8s").mkdir(); (self.project / "k8s/deploy.yaml").write_text("apiVersion: apps/v1\nkind: Deployment\n")
        out = project_cmd(self.project, self.home, "code", "security", check=False).stdout
        self.assertNotIn("not read by this scan", out, out)


if __name__ == "__main__":
    unittest.main()
