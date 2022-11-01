import subprocess


class KubectlClient:

    def __init__(self, kubeconfig: str, context_name: str):

        if not kubeconfig:
            raise ValueError('kubeconfig is required')
        if not context_name:
            raise ValueError('context_name is required')

        self.kubeconfig = kubeconfig
        self.context_name = context_name

    def exec(self,
             pod: str,
             namespace: str,
             commands: list,
             capture_output=False,
             text=False) -> subprocess.CompletedProcess:
        '''Executes a command in a pod'''
        cmd = ['exec']
        cmd.extend([pod])
        cmd.extend(['--namespace', namespace])
        cmd.extend(['--'])
        cmd.extend(commands)

        return self.kubectl(cmd, capture_output, text)

    def kubectl(self, args: list, capture_output=False, text=False) -> subprocess.CompletedProcess:
        '''Executes a kubectl command'''
        cmd = ['kubectl']
        cmd.extend(['--kubeconfig', self.kubeconfig])
        cmd.extend(['--context', self.context_name])

        cmd.extend(args)

        p = subprocess.run(cmd, capture_output=capture_output, text=text)
        return p