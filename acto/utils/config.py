from typing import List


class DeployConfig:

    def __init__(self, method: str, file: str, init: str) -> None:
        self.method = method
        self.file = file
        self.init = init


class AnalysisConfig:

    def __init__(self, github_link: str, commit: str, entrypoint: str, type: str,
                 package: str) -> None:
        self.github_link = github_link
        self.commit = commit
        self.entrypoint = entrypoint
        self.type = type
        self.package = package


class OperatorConfig:

    def __init__(self,
                 deploy: dict,
                 crd_name: str,
                 custom_fields: str,
                 blackbox_custom_fields: str,
                 k8s_fields: str,
                 example_dir: str,
                 seed_custom_resource: str,
                 analysis: dict,
                 num_nodes: int = 4,
                 wait_time: int = 60,
                 context: str = None,
                 custom_oracle: str = None,
                 diff_ignore_fields: List[str] = None) -> None:
        self.deploy = DeployConfig(**deploy)
        self.crd_name = crd_name
        self.custom_fields = custom_fields
        self.blackbox_custom_fields = blackbox_custom_fields
        self.k8s_fields = k8s_fields
        self.custom_oracle = custom_oracle
        self.example_dir = example_dir
        self.context = context
        self.seed_custom_resource = seed_custom_resource
        self.analysis = AnalysisConfig(**analysis)

        self.diff_ignore_fields = []
        if diff_ignore_fields is not None:
            for ignore_field in diff_ignore_fields:
                self.diff_ignore_fields.append(fr"{ignore_field}")


        self.num_nodes = num_nodes
        self.wait_time = wait_time


def OperatorConfigDecoder(obj) -> OperatorConfig:
    return OperatorConfig(**obj)