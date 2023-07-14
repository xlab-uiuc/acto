import subprocess
import tempfile

import kubernetes
import yaml


class KubectlClient:

    def __init__(self, kubeconfig: str, context_name: str):

        if not kubeconfig:
            raise ValueError('kubeconfig is required')
        if not context_name:
            raise ValueError('context_name is required')

        self.kubeconfig = kubeconfig
        self.context_name = context_name
        self.api_client = kubernetes_client(kubeconfig, context_name)

    def exec(self,
             pod: str,
             namespace: str,
             commands: list,
             capture_output=False,
             text=False) -> subprocess.CompletedProcess:
        """Executes a command in a pod"""
        cmd = ['exec']
        cmd.extend([pod])
        cmd.extend(['--namespace', namespace])
        cmd.extend(['--'])
        cmd.extend(commands)

        return self.kubectl(cmd, capture_output, text)

    def kubectl(self,
                args: list,
                capture_output=False,
                text=False,
                timeout: int = 600) -> subprocess.CompletedProcess:
        """Executes a kubectl command"""
        cmd = ['kubectl']
        cmd.extend(['--kubeconfig', self.kubeconfig])
        cmd.extend(['--context', self.context_name])

        cmd.extend(args)

        p = subprocess.run(cmd, capture_output=capture_output, text=text, timeout=timeout)
        return p

    def apply(self, file_content: dict, **kwargs) -> subprocess.CompletedProcess:
        args = {
            'namespace': '-n',
            'server_side': '--server-side',
        }
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.yaml') as f:
            if isinstance(file_content, list):
                yaml.safe_dump_all(file_content, f)
            else:
                yaml.safe_dump(file_content, f)
            cmd = ['apply', '-f', f.name]
            for k, v in kwargs.items():
                if k in args:
                    cmd.extend([args[k]])
                    if v:
                        cmd.extend([v])
                else:
                    raise ValueError(f'Invalid argument {k}')
            return self.kubectl(cmd, capture_output=True, text=True)


def kubernetes_client(kubeconfig: str, context_name: str) -> kubernetes.client.ApiClient:
    return kubernetes.config.kube_config.new_client_from_config(config_file=kubeconfig,
                                                                context=context_name)
